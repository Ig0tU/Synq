
try:
    import numba.core.decorators as _nd
    _nd.JitDispatcher.enable_caching = lambda self: None
except Exception:
    pass

from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory, jsonify
import os
import secrets
from werkzeug.utils import secure_filename
import sys
import shutil
import logging
import json
from datetime import datetime

# Import our new modules
from bulk_processor import get_bulk_processor
from preview_generator import get_preview_generator
from config_manager import get_config_manager

os.environ['NUMBA_CACHE_DIR'] = '/tmp/numba_cache'

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))
import inference2

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['CHECKPOINTS_FOLDER'] = 'checkpoints'
app.config['TEMP_FOLDER'] = 'temp'
app.config['CONFIG_FOLDER'] = 'config'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

ALLOWED_FACE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'aac', 'flac'}
ALLOWED_MODEL_EXTENSIONS = {'pth', 'pt'}

# Ensure directories exist
try:
    for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULTS_FOLDER'], 
                   app.config['CHECKPOINTS_FOLDER'], app.config['TEMP_FOLDER'],
                   app.config['CONFIG_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
    logger.info("All necessary directories ensured to exist.")
except OSError as e:
    logger.critical(f"Error creating essential directories: {e}")
    sys.exit(1)

# Initialize global instances
bulk_processor = get_bulk_processor(app.config['RESULTS_FOLDER'], app.config['TEMP_FOLDER'])
preview_generator = get_preview_generator(app.config['TEMP_FOLDER'])
config_manager = get_config_manager(app.config['CONFIG_FOLDER'])

def allowed_file(filename, allowed_extensions):
    """Checks if a file's extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    """Renders the main page with enhanced features."""
    theme = session.get('theme', 'dark')
    available_models = []
    try:
        model_files = [f for f in os.listdir(app.config['CHECKPOINTS_FOLDER'])
                       if allowed_file(f, ALLOWED_MODEL_EXTENSIONS)]
        available_models = sorted(model_files)
        logger.info(f"Successfully loaded {len(available_models)} models.")
    except FileNotFoundError:
        logger.warning(f"Checkpoints folder '{app.config['CHECKPOINTS_FOLDER']}' not found.")
    except Exception as e:
        logger.error(f"Error loading models: {e}")
    
    # Get presets and user settings
    presets = config_manager.get_presets()
    user_settings = config_manager.get_user_settings()
    micro_change_templates = config_manager.get_micro_change_templates()
    
    return render_template('index.html', 
                         theme=theme, 
                         models=available_models,
                         presets=presets,
                         user_settings=user_settings,
                         micro_change_templates=micro_change_templates)

@app.route('/bulk')
def bulk_processing():
    """Renders the bulk processing page."""
    theme = session.get('theme', 'dark')
    available_models = []
    try:
        model_files = [f for f in os.listdir(app.config['CHECKPOINTS_FOLDER'])
                       if allowed_file(f, ALLOWED_MODEL_EXTENSIONS)]
        available_models = sorted(model_files)
    except Exception as e:
        logger.error(f"Error loading models: {e}")
    
    presets = config_manager.get_presets()
    return render_template('bulk_processing.html', 
                         theme=theme, 
                         models=available_models,
                         presets=presets)

@app.route('/preview')
def preview_page():
    """Renders the preview and comparison page."""
    theme = session.get('theme', 'dark')
    return render_template('preview.html', theme=theme)

@app.route('/toggle_theme')
def toggle_theme():
    """Toggles the session theme between dark and light."""
    current_theme = session.get('theme', 'dark')
    new_theme = 'light' if current_theme == 'dark' else 'dark'
    session['theme'] = new_theme
    
    # Update user settings
    user_settings = config_manager.get_user_settings()
    user_settings['theme'] = new_theme
    config_manager.save_user_settings(user_settings)
    
    logger.info(f"Theme toggled to {new_theme}.")
    return redirect(request.referrer or url_for('index'))

@app.route('/infer', methods=['POST'])
def infer():
    """Enhanced inference with preview generation."""
    if request.method == 'POST':
        logger.info("Inference request received.")

        # Check for file presence
        if 'face_file' not in request.files or 'audio_file' not in request.files:
            flash("Both face and audio files are required for inference.", "error")
            return redirect(url_for('index'))

        face_file = request.files['face_file']
        audio_file = request.files['audio_file']
        selected_model = request.form.get('model_select')
        preset_id = request.form.get('preset_select')

        if face_file.filename == '' or audio_file.filename == '':
            flash("No selected file for face or audio provided.", "error")
            return redirect(url_for('index'))

        if not selected_model:
            flash("No model selected for inference.", "error")
            return redirect(url_for('index'))

        # Validate file types
        if not allowed_file(face_file.filename, ALLOWED_FACE_EXTENSIONS):
            flash(f"Invalid face file type. Allowed: {', '.join(ALLOWED_FACE_EXTENSIONS)}", "error")
            return redirect(url_for('index'))
        
        if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            flash(f"Invalid audio file type. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}", "error")
            return redirect(url_for('index'))

        face_filename = secure_filename(face_file.filename)
        audio_filename = secure_filename(audio_file.filename)

        face_uuid = secrets.token_hex(8)
        audio_uuid = secrets.token_hex(8)

        face_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{face_uuid}_{face_filename}")
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{audio_uuid}_{audio_filename}")

        try:
            face_file.save(face_path)
            audio_file.save(audio_path)
            logger.info(f"Successfully saved uploaded files: {face_path}, {audio_path}")
        except Exception as e:
            logger.error(f"Error saving uploaded files: {e}")
            flash("Error saving uploaded files.", "error")
            return redirect(url_for('index'))

        # Get settings from preset or form
        if preset_id:
            preset = config_manager.get_preset(preset_id)
            if preset:
                settings = preset['settings'].copy()
            else:
                settings = {}
        else:
            settings = {}

        # Apply micro-changes if any
        micro_changes = {}
        for key in request.form:
            if key.startswith('micro_'):
                param_name = key[6:]  # Remove 'micro_' prefix
                try:
                    value = float(request.form[key])
                    micro_changes[param_name] = value
                except ValueError:
                    pass

        if micro_changes:
            settings = config_manager.apply_micro_changes(settings, micro_changes)

        # Override with form values if provided
        form_settings = {
            'static': request.form.get('static_input') == 'on',
            'fps': float(request.form.get('fps', settings.get('fps', 25.0))),
            'resize_factor': int(request.form.get('resize_factor', settings.get('resize_factor', 1))),
            'rotate': request.form.get('rotate') == 'on',
            'nosmooth': request.form.get('nosmooth') == 'on',
        }
        settings.update(form_settings)

        checkpoint_path = os.path.join(app.config['CHECKPOINTS_FOLDER'], selected_model)
        output_video_name = f"result_{face_uuid}.mp4"

        try:
            # Generate previews before processing
            face_preview = preview_generator.generate_face_preview(face_path)
            audio_preview = preview_generator.generate_audio_waveform(audio_path)

            logger.info(f"Starting inference with model: {selected_model}")
            generated_video_path = inference2.run_inference(
                checkpoint_path=checkpoint_path,
                face_path=face_path,
                audio_path=audio_path,
                output_filename=output_video_name,
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

            # Generate comparison preview
            comparison_preview = preview_generator.generate_comparison_preview(
                face_path, generated_video_path
            )

            logger.info(f"Inference completed successfully. Generated video: {generated_video_path}")
            flash("Video generated successfully!", "success")
            
            return redirect(url_for('render_result_page', 
                                  filename=os.path.basename(generated_video_path),
                                  face_preview=os.path.basename(face_preview) if face_preview else None,
                                  audio_preview=os.path.basename(audio_preview) if audio_preview else None,
                                  comparison_preview=os.path.basename(comparison_preview) if comparison_preview else None))

        except ValueError as e:
            logger.error(f"Inference ValueError: {e}")
            flash(f"Processing error: {str(e)}", "error")
        except RuntimeError as e:
            logger.error(f"Runtime Error during inference: {e}")
            flash(f"Runtime error: {str(e)}", "error")
        except Exception as e:
            logger.critical(f"An unexpected error occurred during inference: {e}", exc_info=True)
            flash("An unexpected error occurred during processing.", "error")
        finally:
            # Clean up uploaded files
            for file_path in [face_path, audio_path]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up uploaded file: {file_path}")
                    except OSError as e:
                        logger.error(f"Error removing file {file_path}: {e}")

    return redirect(url_for('index'))

@app.route('/bulk_infer', methods=['POST'])
def bulk_infer():
    """Handle bulk processing requests."""
    try:
        data = request.get_json()
        
        if not data or 'file_pairs' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        file_pairs = data['file_pairs']
        model_name = data.get('model', '')
        preset_id = data.get('preset_id', '')
        
        if not model_name:
            return jsonify({'error': 'Model selection required'}), 400
        
        # Get settings from preset
        settings = {}
        if preset_id:
            preset = config_manager.get_preset(preset_id)
            if preset:
                settings = preset['settings']
        
        # Apply any micro-changes
        micro_changes = data.get('micro_changes', {})
        if micro_changes:
            settings = config_manager.apply_micro_changes(settings, micro_changes)
        
        model_path = os.path.join(app.config['CHECKPOINTS_FOLDER'], model_name)
        
        job_config = {
            'file_pairs': file_pairs,
            'model_path': model_path,
            'settings': settings
        }
        
        job_id = bulk_processor.add_bulk_job(job_config)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Bulk job started with {len(file_pairs)} file pairs'
        })
        
    except Exception as e:
        logger.error(f"Error starting bulk job: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/bulk_status/<job_id>')
def bulk_status(job_id):
    """Get status of a bulk processing job."""
    try:
        status = bulk_processor.get_job_status(job_id)
        if status:
            return jsonify(status)
        else:
            return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/bulk_jobs')
def bulk_jobs():
    """Get status of all bulk processing jobs."""
    try:
        jobs = bulk_processor.get_all_jobs()
        return jsonify(jobs)
    except Exception as e:
        logger.error(f"Error getting all jobs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/cancel_job/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel a bulk processing job."""
    try:
        success = bulk_processor.cancel_job(job_id)
        if success:
            return jsonify({'success': True, 'message': 'Job cancelled'})
        else:
            return jsonify({'error': 'Job not found or cannot be cancelled'}), 404
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_preview', methods=['POST'])
def generate_preview():
    """Generate preview for uploaded files."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        file_type = request.form.get('type', 'face')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save temporary file
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['TEMP_FOLDER'], f"preview_{temp_filename}")
        file.save(temp_path)
        
        try:
            if file_type == 'face':
                preview_path = preview_generator.generate_face_preview(temp_path)
            elif file_type == 'audio':
                preview_path = preview_generator.generate_audio_waveform(temp_path)
            else:
                return jsonify({'error': 'Invalid file type'}), 400
            
            if preview_path:
                preview_url = url_for('serve_temp_file', filename=os.path.basename(preview_path))
                return jsonify({'success': True, 'preview_url': preview_url})
            else:
                return jsonify({'error': 'Failed to generate preview'}), 500
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/presets', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_presets():
    """Manage configuration presets."""
    try:
        if request.method == 'GET':
            presets = config_manager.get_presets()
            return jsonify(presets)
        
        elif request.method == 'POST':
            data = request.get_json()
            name = data.get('name', '')
            description = data.get('description', '')
            settings = data.get('settings', {})
            
            if not name or not settings:
                return jsonify({'error': 'Name and settings required'}), 400
            
            preset_id = config_manager.create_preset(name, description, settings)
            return jsonify({'success': True, 'preset_id': preset_id})
        
        elif request.method == 'PUT':
            data = request.get_json()
            preset_id = data.get('preset_id', '')
            
            if not preset_id:
                return jsonify({'error': 'Preset ID required'}), 400
            
            success = config_manager.update_preset(
                preset_id,
                data.get('name'),
                data.get('description'),
                data.get('settings')
            )
            
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Preset not found'}), 404
        
        elif request.method == 'DELETE':
            data = request.get_json()
            preset_id = data.get('preset_id', '')
            
            if not preset_id:
                return jsonify({'error': 'Preset ID required'}), 400
            
            success = config_manager.delete_preset(preset_id)
            
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Preset not found or cannot be deleted'}), 404
                
    except Exception as e:
        logger.error(f"Error managing presets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/user_settings', methods=['GET', 'POST'])
def manage_user_settings():
    """Manage user settings."""
    try:
        if request.method == 'GET':
            settings = config_manager.get_user_settings()
            return jsonify(settings)
        
        elif request.method == 'POST':
            data = request.get_json()
            config_manager.save_user_settings(data)
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Error managing user settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/result_page/<filename>')
def render_result_page(filename):
    """Renders the enhanced result page with previews."""
    theme = session.get('theme', 'dark')
    result_video_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    
    if not os.path.exists(result_video_path):
        logger.warning(f"Attempted to access non-existent result video: {result_video_path}")
        flash("Result video not found.", "error")
        return redirect(url_for('index'))
    
    # Get preview files from query parameters
    face_preview = request.args.get('face_preview')
    audio_preview = request.args.get('audio_preview')
    comparison_preview = request.args.get('comparison_preview')
    
    # Get video info
    video_info = preview_generator.get_video_info(result_video_path)
    
    logger.info(f"Rendering result page for video: {filename}")
    return render_template('result.html', 
                         theme=theme, 
                         video_filename=filename,
                         video_info=video_info,
                         face_preview=face_preview,
                         audio_preview=audio_preview,
                         comparison_preview=comparison_preview)

@app.route('/results/<path:filename>')
def serve_result_video(filename):
    """Serves the generated video file from the results folder."""
    logger.debug(f"Serving result video: {filename}")
    try:
        return send_from_directory(app.config['RESULTS_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Error serving result video {filename}: {e}")
        return "Error serving file", 500

@app.route('/temp/<path:filename>')
def serve_temp_file(filename):
    """Serves temporary files like previews."""
    try:
        return send_from_directory(app.config['TEMP_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Error serving temp file {filename}: {e}")
        return "Error serving file", 500

@app.route('/download/<filename>')
def download_result(filename):
    """Allows downloading the generated video file."""
    logger.info(f"Download request for video: {filename}")
    try:
        return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading video {filename}: {e}")
        return "Error downloading file", 500

@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up old files and previews."""
    try:
        # Clean up old previews
        preview_generator.cleanup_previews()
        
        # Clean up old result files (older than 7 days)
        import time
        current_time = time.time()
        cleaned_count = 0
        
        for filename in os.listdir(app.config['RESULTS_FOLDER']):
            file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
            file_age = current_time - os.path.getmtime(file_path)
            
            if file_age > 7 * 24 * 3600:  # 7 days
                os.remove(file_path)
                cleaned_count += 1
        
        return jsonify({
            'success': True, 
            'message': f'Cleaned up {cleaned_count} old files'
        })
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Directories are already ensured at the top level
    try:
        for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULTS_FOLDER'], 
                       app.config['CHECKPOINTS_FOLDER'], app.config['TEMP_FOLDER'],
                       app.config['CONFIG_FOLDER']]:
            os.makedirs(folder, exist_ok=True)
        logger.info("Application directories confirmed at startup.")
    except OSError as e:
        logger.critical(f"Critical error during startup: {e}")
        sys.exit(1)

    logger.info("Starting enhanced Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)
