from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
import os
import secrets
from werkzeug.utils import secure_filename
import sys
import shutil

sys.path.append(os.path.dirname(__file__))
import inference2 # Import your refactored inference script

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results' # This directory is NOT inside static
app.config['CHECKPOINTS_FOLDER'] = 'checkpoints'
app.config['TEMP_FOLDER'] = 'temp'

ALLOWED_FACE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'aac', 'flac'}
ALLOWED_MODEL_EXTENSIONS = {'pth', 'pt'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['CHECKPOINTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)


def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    theme = session.get('theme', 'dark')
    available_models = []
    try:
        model_files = [f for f in os.listdir(app.config['CHECKPOINTS_FOLDER'])
                       if allowed_file(f, ALLOWED_MODEL_EXTENSIONS)]
        available_models = sorted(model_files)
    except FileNotFoundError:
        # flash("Checkpoints folder not found. Please create a 'checkpoints' directory.", 'error') # Messages removed
        pass
    except Exception as e:
        # flash(f"Error loading models: {e}", 'error') # Messages removed
        pass
    return render_template('index.html', theme=theme, models=available_models)

@app.route('/toggle_theme')
def toggle_theme():
    current_theme = session.get('theme', 'dark')
    if current_theme == 'dark':
        session['theme'] = 'light'
    else:
        session['theme'] = 'dark'
    return redirect(request.referrer or url_for('index'))

@app.route('/infer', methods=['POST'])
def infer():
    if request.method == 'POST':
        if 'face_file' not in request.files or 'audio_file' not in request.files:
            # flash('Both face and audio files are required.', 'error') # Messages removed
            return redirect(url_for('index'))

        face_file = request.files['face_file']
        audio_file = request.files['audio_file']
        selected_model = request.form.get('model_select')

        if face_file.filename == '' or audio_file.filename == '':
            # flash('No selected file for face or audio.', 'error') # Messages removed
            return redirect(url_for('index'))

        if not selected_model:
            # flash('No model selected.', 'error') # Messages removed
            return redirect(url_for('index'))

        if not allowed_file(face_file.filename, ALLOWED_FACE_EXTENSIONS):
            # flash('Invalid face file type. Allowed: png, jpg, jpeg, mp4, avi, mov', 'error') # Messages removed
            return redirect(url_for('index'))
        if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            # flash('Invalid audio file type. Allowed: wav, mp3, aac, flac', 'error') # Messages removed
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
        except Exception as e:
            # flash(f"Error saving uploaded files: {e}", 'error') # Messages removed
            return redirect(url_for('index'))

        checkpoint_path = os.path.join(app.config['CHECKPOINTS_FOLDER'], selected_model)
        output_video_name = f"result_{face_uuid}.mp4"

        try:
            # flash('Starting inference... This may take a while.', 'info') # Messages removed
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
                face_det_batch_size=16,
                wav2lip_batch_size=128,
                img_size=96
            )
            # flash('Inference completed successfully!', 'success') # Messages removed
            
            # Redirect to the page that renders result.html
            return redirect(url_for('render_result_page', filename=os.path.basename(generated_video_path)))

        except ValueError as e:
            # flash(f"Inference Error: {e}", 'error') # Messages removed
            pass
        except RuntimeError as e:
            # flash(f"Runtime Error during inference: {e}", 'error') # Messages removed
            pass
        except Exception as e:
            # flash(f"An unexpected error occurred: {e}", 'error') # Messages removed
            pass
        finally:
            if os.path.exists(face_path):
                os.remove(face_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)

    return redirect(url_for('index'))

# Route to render the result.html template
@app.route('/result_page/<filename>')
def render_result_page(filename):
    theme = session.get('theme', 'dark')
    # Check if the file actually exists before rendering
    if not os.path.exists(os.path.join(app.config['RESULTS_FOLDER'], filename)):
        # If the video isn't found, redirect or show an error
        # Consider a dedicated error page or a message within index.html if no flashes are used
        return redirect(url_for('index'))
    return render_template('result.html', theme=theme, video_filename=filename)


# Route to serve the video file itself (used by <video src="...">)
@app.route('/results/<path:filename>') # Use <path:filename> to handle potential subdirectories in filename (though not needed here)
def serve_result_video(filename):
    # This route is solely for serving the video file
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

# Route to download the video file
@app.route('/download/<filename>') # Changed to /download/ for clarity
def download_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHECKPOINTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

    app.run(debug=True)