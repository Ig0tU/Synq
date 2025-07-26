

try:
    import numba.core.decorators as _nd
    _nd.JitDispatcher.enable_caching = lambda self: None
except Exception:
    pass
    
from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
import os
import secrets
from werkzeug.utils import secure_filename
import sys
import shutil
import logging # Import the logging module


os.environ['NUMBA_CACHE_DIR'] = '/tmp/numba_cache' # Or any other writable directory

# Configure logging
logging.basicConfig(level=logging.INFO, # Set the minimum logging level
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"), # Log to a file
                        logging.StreamHandler()        # Log to console
                    ])
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))
import inference2 # Import your refactored inference script

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['CHECKPOINTS_FOLDER'] = 'checkpoints'
app.config['TEMP_FOLDER'] = 'temp'

ALLOWED_FACE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'aac', 'flac'}
ALLOWED_MODEL_EXTENSIONS = {'pth', 'pt'}

# Ensure directories exist
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHECKPOINTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
    logger.info("All necessary directories ensured to exist.")
except OSError as e:
    logger.critical(f"Error creating essential directories: {e}")
    # Depending on the severity, you might want to exit or disable functionality
    sys.exit(1) # Exit if essential directories cannot be created

def allowed_file(filename, allowed_extensions):
    """Checks if a file's extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    """Renders the main page, displaying available models."""
    theme = session.get('theme', 'dark')
    available_models = []
    try:
        model_files = [f for f in os.listdir(app.config['CHECKPOINTS_FOLDER'])
                       if allowed_file(f, ALLOWED_MODEL_EXTENSIONS)]
        available_models = sorted(model_files)
        logger.info(f"Successfully loaded {len(available_models)} models.")
    except FileNotFoundError:
        logger.warning(f"Checkpoints folder '{app.config['CHECKPOINTS_FOLDER']}' not found. Please create it.")
    except Exception as e:
        logger.error(f"Error loading models from '{app.config['CHECKPOINTS_FOLDER']}': {e}")
    return render_template('index.html', theme=theme, models=available_models)

@app.route('/toggle_theme')
def toggle_theme():
    """Toggles the session theme between dark and light."""
    current_theme = session.get('theme', 'dark')
    if current_theme == 'dark':
        session['theme'] = 'light'
        logger.info("Theme toggled to light.")
    else:
        session['theme'] = 'dark'
        logger.info("Theme toggled to dark.")
    return redirect(request.referrer or url_for('index'))

@app.route('/infer', methods=['POST'])
def infer():
    """Handles the inference request, processing uploaded files and running the model."""
    if request.method == 'POST':
        logger.info("Inference request received.")

        # Check for file presence
        if 'face_file' not in request.files or 'audio_file' not in request.files:
            logger.warning("Both face and audio files are required for inference.")
            return redirect(url_for('index'))

        face_file = request.files['face_file']
        audio_file = request.files['audio_file']
        selected_model = request.form.get('model_select')

        if face_file.filename == '' or audio_file.filename == '':
            logger.warning("No selected file for face or audio provided.")
            return redirect(url_for('index'))

        if not selected_model:
            logger.warning("No model selected for inference.")
            return redirect(url_for('index'))

        # Validate file types
        if not allowed_file(face_file.filename, ALLOWED_FACE_EXTENSIONS):
            logger.warning(f"Invalid face file type: {face_file.filename}. Allowed: {', '.join(ALLOWED_FACE_EXTENSIONS)}")
            return redirect(url_for('index'))
        if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            logger.warning(f"Invalid audio file type: {audio_file.filename}. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")
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
            return redirect(url_for('index'))

        checkpoint_path = os.path.join(app.config['CHECKPOINTS_FOLDER'], selected_model)
        output_video_name = f"result_{face_uuid}.mp4"

        try:
            logger.info(f"Starting inference with model: {selected_model}, face: {face_filename}, audio: {audio_filename}")
            generated_video_path = inference2.run_inference(
                checkpoint_path=checkpoint_path,
                face_path=face_path,
                audio_path=audio_path,
                output_filename=output_video_name,
                static=request.form.get('static_input') == 'on',
                fps=float(request.form.get('fps', 25.0)),
                resize_factor=int(request.form.get('resize_factor', 1)),
                rotate=request.form.get('rotate') == 'on',
                nosmooth=request.form.get('nosmooth') == 'on',
                pads=[0, 10, 0, 0],
                crop=[0, -1, 0, -1],
                box=[-1, -1, -1, -1],
                face_det_batch_size=8,
                wav2lip_batch_size=64,
                #face_det_batch_size=16,
                #wav2lip_batch_size=128,
                img_size=96
            )
            logger.info(f"Inference completed successfully. Generated video: {generated_video_path}")
            return redirect(url_for('render_result_page', filename=os.path.basename(generated_video_path)))

        except ValueError as e:
            logger.error(f"Inference ValueError: {e}")
        except RuntimeError as e:
            logger.error(f"Runtime Error during inference: {e}")
        except Exception as e:
            logger.critical(f"An unexpected error occurred during inference: {e}", exc_info=True) # exc_info=True to log traceback
        finally:
            # Clean up uploaded files regardless of inference success or failure
            if os.path.exists(face_path):
                try:
                    os.remove(face_path)
                    logger.info(f"Cleaned up uploaded face file: {face_path}")
                except OSError as e:
                    logger.error(f"Error removing face file {face_path}: {e}")
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.info(f"Cleaned up uploaded audio file: {audio_path}")
                except OSError as e:
                    logger.error(f"Error removing audio file {audio_path}: {e}")

    return redirect(url_for('index'))


## Result Handling and File Serving

@app.route('/result_page/<filename>')
def render_result_page(filename):
    """Renders the result page with the generated video."""
    theme = session.get('theme', 'dark')
    result_video_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    if not os.path.exists(result_video_path):
        logger.warning(f"Attempted to access non-existent result video: {result_video_path}")
        return redirect(url_for('index'))
    logger.info(f"Rendering result page for video: {filename}")
    return render_template('result.html', theme=theme, video_filename=filename)

@app.route('/results/<path:filename>')
def serve_result_video(filename):
    """Serves the generated video file from the results folder."""
    logger.debug(f"Serving result video: {filename}")
    try:
        return send_from_directory(app.config['RESULTS_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Error serving result video {filename}: {e}")
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

## Application Initialization

if __name__ == '__main__':
    # Directories are already ensured at the top level of the script,
    # but re-checking here for robustness in case app.run is called differently.
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
        os.makedirs(app.config['CHECKPOINTS_FOLDER'], exist_ok=True)
        os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
        logger.info("Application directories confirmed at startup.")
    except OSError as e:
        logger.critical(f"Critical error during startup: Could not create necessary directories: {e}")
        sys.exit(1) # Exit if directories cannot be created

    logger.info("Starting Flask application...")
    # In a production environment, debug=True should be False
    app.run(host="0.0.0.0", port=5000, debug=True)