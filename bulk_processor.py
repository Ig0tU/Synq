
import os
import json
import uuid
import threading
import time
from datetime import datetime
from queue import Queue, Empty
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class BulkProcessor:
    def __init__(self, results_folder: str, temp_folder: str):
        self.results_folder = results_folder
        self.temp_folder = temp_folder
        self.job_queue = Queue()
        self.active_jobs = {}
        self.completed_jobs = {}
        self.failed_jobs = {}
        self.worker_thread = None
        self.is_running = False
        
    def start_worker(self):
        """Start the background worker thread"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Bulk processor worker started")
    
    def stop_worker(self):
        """Stop the background worker thread"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Bulk processor worker stopped")
    
    def add_bulk_job(self, job_config: Dict) -> str:
        """Add a bulk processing job to the queue"""
        job_id = str(uuid.uuid4())
        job_data = {
            'id': job_id,
            'config': job_config,
            'created_at': datetime.now().isoformat(),
            'status': 'queued',
            'progress': 0,
            'total_files': len(job_config.get('file_pairs', [])),
            'processed_files': 0,
            'failed_files': 0,
            'results': []
        }
        
        self.job_queue.put(job_data)
        self.active_jobs[job_id] = job_data
        logger.info(f"Added bulk job {job_id} with {job_data['total_files']} files")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the status of a specific job"""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        elif job_id in self.completed_jobs:
            return self.completed_jobs[job_id]
        elif job_id in self.failed_jobs:
            return self.failed_jobs[job_id]
        return None
    
    def get_all_jobs(self) -> Dict:
        """Get status of all jobs"""
        return {
            'active': list(self.active_jobs.values()),
            'completed': list(self.completed_jobs.values()),
            'failed': list(self.failed_jobs.values()),
            'queue_size': self.job_queue.qsize()
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job['status'] = 'cancelled'
            job['cancelled_at'] = datetime.now().isoformat()
            self.failed_jobs[job_id] = self.active_jobs.pop(job_id)
            logger.info(f"Cancelled job {job_id}")
            return True
        return False
    
    def _worker_loop(self):
        """Main worker loop for processing jobs"""
        while self.is_running:
            try:
                # Get job from queue with timeout
                job_data = self.job_queue.get(timeout=1)
                self._process_bulk_job(job_data)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
    
    def _process_bulk_job(self, job_data: Dict):
        """Process a single bulk job"""
        job_id = job_data['id']
        
        try:
            job_data['status'] = 'processing'
            job_data['started_at'] = datetime.now().isoformat()
            
            file_pairs = job_data['config']['file_pairs']
            model_path = job_data['config']['model_path']
            settings = job_data['config'].get('settings', {})
            
            for i, (face_file, audio_file) in enumerate(file_pairs):
                if job_data['status'] == 'cancelled':
                    break
                
                try:
                    # Process individual file pair
                    result = self._process_file_pair(
                        face_file, audio_file, model_path, settings, job_id, i
                    )
                    job_data['results'].append(result)
                    job_data['processed_files'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process file pair {i} in job {job_id}: {e}")
                    job_data['failed_files'] += 1
                    job_data['results'].append({
                        'index': i,
                        'face_file': face_file,
                        'audio_file': audio_file,
                        'status': 'failed',
                        'error': str(e)
                    })
                
                # Update progress
                job_data['progress'] = int((i + 1) / len(file_pairs) * 100)
            
            # Mark job as completed or failed
            if job_data['status'] != 'cancelled':
                if job_data['failed_files'] == 0:
                    job_data['status'] = 'completed'
                    job_data['completed_at'] = datetime.now().isoformat()
                    self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
                else:
                    job_data['status'] = 'completed_with_errors'
                    job_data['completed_at'] = datetime.now().isoformat()
                    self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
            
        except Exception as e:
            logger.error(f"Critical error processing bulk job {job_id}: {e}")
            job_data['status'] = 'failed'
            job_data['error'] = str(e)
            job_data['failed_at'] = datetime.now().isoformat()
            self.failed_jobs[job_id] = self.active_jobs.pop(job_id)
    
    def _process_file_pair(self, face_file: str, audio_file: str, 
                          model_path: str, settings: Dict, job_id: str, index: int) -> Dict:
        """Process a single face/audio file pair"""
        try:
            # Import inference module
            import inference2
            
            # Generate unique output filename
            output_filename = f"bulk_{job_id}_{index:03d}.mp4"
            
            # Run inference
            result_path = inference2.run_inference(
                checkpoint_path=model_path,
                face_path=face_file,
                audio_path=audio_file,
                output_filename=output_filename,
                static=settings.get('static', False),
                fps=settings.get('fps', 25.0),
                resize_factor=settings.get('resize_factor', 1),
                rotate=settings.get('rotate', False),
                nosmooth=settings.get('nosmooth', False),
                pads=settings.get('pads', [0, 10, 0, 0]),
                crop=settings.get('crop', [0, -1, 0, -1]),
                box=settings.get('box', [-1, -1, -1, -1]),
                face_det_batch_size=settings.get('face_det_batch_size', 8),
                wav2lip_batch_size=settings.get('wav2lip_batch_size', 64),
                img_size=settings.get('img_size', 96)
            )
            
            return {
                'index': index,
                'face_file': os.path.basename(face_file),
                'audio_file': os.path.basename(audio_file),
                'output_file': output_filename,
                'output_path': result_path,
                'status': 'success',
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Failed to process file pair: {e}")

# Global bulk processor instance
bulk_processor = None

def get_bulk_processor(results_folder: str, temp_folder: str) -> BulkProcessor:
    """Get or create the global bulk processor instance"""
    global bulk_processor
    if bulk_processor is None:
        bulk_processor = BulkProcessor(results_folder, temp_folder)
        bulk_processor.start_worker()
    return bulk_processor
