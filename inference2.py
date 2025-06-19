# inference.py (Updated)
import audio
from os import listdir, path
import numpy as np
import scipy, cv2, os, sys, argparse, audio
import json, subprocess, random, string
from tqdm import tqdm
from glob import glob
import torch # Ensure torch is imported
try:
    import face_detection # Assuming this is installed or in a path accessible by your Flask app
except ImportError:
    print("face_detection not found. Please ensure it's installed or available in your PYTHONPATH.")
    # You might want to raise an error or handle this gracefully if face_detection is truly optional.

# Make sure you have a models/Wav2Lip.py or similar structure
try:
    from models import Wav2Lip
except ImportError:
    print("Wav2Lip model not found. Please ensure models/Wav2Lip.py exists and is correctly configured.")
    # You might want to raise an error or handle this gracefully.

import platform
import shutil # For clearing temp directory


# These globals are still useful for shared configuration
mel_step_size = 16
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Inference script using {} for inference.'.format(device))


def get_smoothened_boxes(boxes, T):
    for i in range(len(boxes)):
        if i + T > len(boxes):
            window = boxes[len(boxes) - T:]
        else:
            window = boxes[i : i + T]
        boxes[i] = np.mean(window, axis=0)
    return boxes

def face_detect(images, pads, face_det_batch_size, nosmooth, img_size):
    detector = face_detection.FaceAlignment(face_detection.LandmarksType._2D,
                                            flip_input=False, device=device)

    batch_size = face_det_batch_size

    while 1:
        predictions = []
        try:
            for i in tqdm(range(0, len(images), batch_size), desc="Face Detection"):
                predictions.extend(detector.get_detections_for_batch(np.array(images[i:i + batch_size])))
        except RuntimeError as e:
            if batch_size == 1:
                raise RuntimeError(f'Image too big to run face detection on GPU. Error: {e}')
            batch_size //= 2
            print('Recovering from OOM error; New face detection batch size: {}'.format(batch_size))
            continue
        break

    results = []
    pady1, pady2, padx1, padx2 = pads
    for rect, image in zip(predictions, images):
        if rect is None:
            # Save the faulty frame for debugging
            output_dir = 'temp' # Ensure this exists or create it
            os.makedirs(output_dir, exist_ok=True)
            cv2.imwrite(os.path.join(output_dir, 'faulty_frame.jpg'), image)
            raise ValueError('Face not detected! Ensure the video/image contains a face in all the frames or try adjusting pads/box.')

        y1 = max(0, rect[1] - pady1)
        y2 = min(image.shape[0], rect[3] + pady2)
        x1 = max(0, rect[0] - padx1)
        x2 = min(image.shape[1], rect[2] + padx2)

        results.append([x1, y1, x2, y2])

    boxes = np.array(results)
    if not nosmooth: boxes = get_smoothened_boxes(boxes, T=5)
    results = [[image[y1: y2, x1:x2], (y1, y2, x1, x2)] for image, (x1, y1, x2, y2) in zip(images, boxes)]

    del detector # Clean up detector
    return results

def datagen(frames, mels, box, static, wav2lip_batch_size, img_size, pads, face_det_batch_size, nosmooth):
    img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

    if box[0] == -1:
        if not static:
            face_det_results = face_detect(frames, pads, face_det_batch_size, nosmooth, img_size) # BGR2RGB for CNN face detection
        else:
            face_det_results = face_detect([frames[0]], pads, face_det_batch_size, nosmooth, img_size)
    else:
        print('Using the specified bounding box instead of face detection...')
        y1, y2, x1, x2 = box
        face_det_results = [[f[y1: y2, x1:x2], (y1, y2, x1, x2)] for f in frames]

    for i, m in enumerate(mels):
        idx = 0 if static else i % len(frames)
        frame_to_save = frames[idx].copy()
        face, coords = face_det_results[idx].copy()

        face = cv2.resize(face, (img_size, img_size))

        img_batch.append(face)
        mel_batch.append(m)
        frame_batch.append(frame_to_save)
        coords_batch.append(coords)

        if len(img_batch) >= wav2lip_batch_size:
            img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

            img_masked = img_batch.copy()
            img_masked[:, img_size//2:] = 0

            img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
            mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

            yield img_batch, mel_batch, frame_batch, coords_batch
            img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

    if len(img_batch) > 0:
        img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

        img_masked = img_batch.copy()
        img_masked[:, img_size//2:] = 0

        img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
        mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

        yield img_batch, mel_batch, frame_batch, coords_batch

def _load(checkpoint_path):
    # Use torch.jit.load for TorchScript archives
    if device == 'cuda':
        model = torch.jit.load(checkpoint_path)
    else:
        # Accepts string or torch.device, not a lambda
        model = torch.jit.load(checkpoint_path, map_location='cpu')
    return model

def load_model(path):
    print("Loading scripted model from:", path)
    model = _load(path) # returns the TorchScript Module
    model = model.to(device) # move to CPU or GPU
    return model.eval() # set to eval() mode


# New function to be called from Flask app
def run_inference(
    checkpoint_path: str,
    face_path: str,
    audio_path: str,
    output_filename: str,
    static: bool = False,
    fps: float = 25.,
    pads: list = [0, 10, 0, 0],
    face_det_batch_size: int = 16,
    wav2lip_batch_size: int = 128,
    resize_factor: int = 1,
    crop: list = [0, -1, 0, -1],
    box: list = [-1, -1, -1, -1],
    rotate: bool = False,
    nosmooth: bool = False,
    img_size: int = 96 # Fixed for Wav2Lip
) -> str:
    """
    Runs the Wav2Lip inference process.

    Args:
        checkpoint_path (str): Path to the Wav2Lip model checkpoint.
        face_path (str): Path to the input video/image file with a face.
        audio_path (str): Path to the input audio file.
        output_filename (str): Name of the output video file (e.g., 'result.mp4').
        static (bool): If True, use only the first video frame for inference.
        fps (float): Frames per second for static image input.
        pads (list): Padding for face detection (top, bottom, left, right).
        face_det_batch_size (int): Batch size for face detection.
        wav2lip_batch_size (int): Batch size for Wav2Lip model(s).
        resize_factor (int): Reduce the resolution by this factor.
        crop (list): Crop video to a smaller region (top, bottom, left, right).
        box (list): Constant bounding box for the face.
        rotate (bool): Rotate video right by 90deg.
        nosmooth (bool): Prevent smoothing face detections.
        img_size (int): Image size for the model.

    Returns:
        str: The path to the generated output video file.
    """
    print(f"Starting inference with: face='{face_path}', audio='{audio_path}', checkpoint='{checkpoint_path}', outfile='{output_filename}'")

    # Create necessary directories
    output_dir = 'results'
    temp_dir = 'temp'
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    # Clear temp directory for fresh run
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

    # Determine if input is static based on file extension
    is_static_input = static or (os.path.isfile(face_path) and face_path.split('.')[-1].lower() in ['jpg', 'png', 'jpeg'])

    full_frames = []
    if is_static_input:
        full_frames = [cv2.imread(face_path)]
        if full_frames[0] is None:
            raise ValueError(f"Could not read face image at: {face_path}")
    else:
        video_stream = cv2.VideoCapture(face_path)
        if not video_stream.isOpened():
            raise ValueError(f"Could not open video file at: {face_path}")
        fps = video_stream.get(cv2.CAP_PROP_FPS)

        print('Reading video frames...')
        while 1:
            still_reading, frame = video_stream.read()
            if not still_reading:
                video_stream.release()
                break
            if resize_factor > 1:
                frame = cv2.resize(frame, (frame.shape[1]//resize_factor, frame.shape[0]//resize_factor))

            if rotate:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            y1, y2, x1, x2 = crop
            if x2 == -1: x2 = frame.shape[1]
            if y2 == -1: y2 = frame.shape[0]

            frame = frame[y1:y2, x1:x2]
            full_frames.append(frame)

    print ("Number of frames available for inference: "+str(len(full_frames)))
    if not full_frames:
        raise ValueError("No frames could be read from the input face file.")

    temp_audio_path = os.path.join(temp_dir, 'temp_audio.wav')
    if not audio_path.endswith('.wav'):
        print('Extracting raw audio...')
        command = f'ffmpeg -y -i "{audio_path}" -strict -2 "{temp_audio_path}"'
        try:
            subprocess.run(command, shell=True, check=True, capture_output=True)
            audio_path = temp_audio_path
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to extract audio from {audio_path}. Error: {e.stderr.decode()}")
    else:
        # Copy the wav file to temp if it's already wav to maintain consistency in naming
        shutil.copy(audio_path, temp_audio_path)
        audio_path = temp_audio_path


    wav = audio.load_wav(audio_path, 16000)
    mel = audio.melspectrogram(wav)
    print("Mel spectrogram shape:", mel.shape)

    if np.isnan(mel.reshape(-1)).sum() > 0:
        raise ValueError('Mel contains nan! Using a TTS voice? Add a small epsilon noise to the wav file and try again')

    mel_chunks = []
    mel_idx_multiplier = 80./fps
    i = 0
    while 1:
        start_idx = int(i * mel_idx_multiplier)
        if start_idx + mel_step_size > len(mel[0]):
            mel_chunks.append(mel[:, len(mel[0]) - mel_step_size:])
            break
        mel_chunks.append(mel[:, start_idx : start_idx + mel_step_size])
        i += 1

    print("Length of mel chunks: {}".format(len(mel_chunks)))

    # Ensure full_frames matches mel_chunks length, or loop if static
    if not is_static_input:
        full_frames = full_frames[:len(mel_chunks)]
    else:
        # If static, replicate the first frame for the duration of the audio
        full_frames = [full_frames[0]] * len(mel_chunks)


    gen = datagen(full_frames.copy(), mel_chunks, box, is_static_input, wav2lip_batch_size, img_size, pads, face_det_batch_size, nosmooth)

    output_avi_path = os.path.join(temp_dir, 'result.avi')

    model_loaded = False
    model = None
    frame_h, frame_w = 0, 0
    out = None

    for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(gen, desc="Wav2Lip Inference",
                                            total=int(np.ceil(float(len(mel_chunks))/wav2lip_batch_size)))):
        if not model_loaded:
            model = load_model(checkpoint_path)
            model_loaded = True
            print ("Model loaded successfully")

            frame_h, frame_w = full_frames[0].shape[:-1]
            out = cv2.VideoWriter(output_avi_path,
                                    cv2.VideoWriter_fourcc(*'DIVX'), fps, (frame_w, frame_h))
        if out is None: # In case no frames were generated for some reason
            raise RuntimeError("Video writer could not be initialized.")


        img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(device)
        mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(device)

        with torch.no_grad():
            pred = model(mel_batch, img_batch)

        pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.

        for p, f, c in zip(pred, frames, coords):
            y1, y2, x1, x2 = c
            p = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))

            f[y1:y2, x1:x2] = p
            out.write(f)

    if out:
        out.release()
    else:
        print("Warning: Video writer was not initialized or no frames were processed.")


    final_output_path = os.path.join(output_dir, output_filename)
    command = f'ffmpeg -y -i "{audio_path}" -i "{output_avi_path}" -strict -2 -q:v 1 "{final_output_path}"'

    try:
        subprocess.run(command, shell=True, check=True, capture_output=True)
        print(f"Output saved to: {final_output_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg final merge error: {e.stderr.decode()}")
        raise RuntimeError(f"Failed to merge audio and video. Error: {e.stderr.decode()}")

    # Clean up temporary files (optional, but good practice)
    # shutil.rmtree(temp_dir) # Be careful with this if you want to inspect temp files

    return final_output_path

# No `if __name__ == '__main__':` block here, as it's meant to be imported