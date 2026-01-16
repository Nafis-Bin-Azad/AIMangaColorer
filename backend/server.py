"""
Flask API Server for Electron GUI.
Provides REST endpoints and WebSocket for real-time progress updates.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional
import threading

# Add parent directory to path for imports when run as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

# Use absolute imports that work both as module and script
try:
    from .colorizer import MangaColorizer
    from .config import FLASK_HOST, FLASK_PORT, OUTPUT_DIR, SUPPORTED_FORMATS
except ImportError:
    from backend.colorizer import MangaColorizer
    from backend.config import FLASK_HOST, FLASK_PORT, OUTPUT_DIR, SUPPORTED_FORMATS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'manga-colorizer-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Enable CORS for Electron
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Global colorizer instance
colorizer: Optional[MangaColorizer] = None
colorization_thread: Optional[threading.Thread] = None
is_processing = False


def get_colorizer() -> MangaColorizer:
    """Get or create the global colorizer instance."""
    global colorizer
    if colorizer is None:
        logger.info("Initializing colorizer")
        colorizer = MangaColorizer()
    return colorizer


def emit_progress(current: int, total: int, filename: str):
    """Emit progress update via WebSocket."""
    progress_data = {
        'current': current,
        'total': total,
        'filename': filename,
        'percent': int((current / total) * 100) if total > 0 else 0
    }
    socketio.emit('progress', progress_data)
    logger.debug(f"Progress: {current}/{total} - {filename}")


def emit_status(status: str, message: str = ""):
    """Emit status update via WebSocket."""
    socketio.emit('status', {'status': status, 'message': message})
    logger.info(f"Status: {status} - {message}")


# REST API Endpoints

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status."""
    return jsonify({
        'status': 'running',
        'processing': is_processing,
        'colorizer_initialized': colorizer is not None
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    try:
        col = get_colorizer()
        config = col.get_model_info()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/api/colorize', methods=['POST'])
def colorize():
    """Colorize uploaded image(s)."""
    global is_processing, colorization_thread
    
    if is_processing:
        return jsonify({
            'success': False,
            'error': 'Already processing'
        }), 409
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        # Get options
        create_zip = request.form.get('create_zip', 'false').lower() == 'true'
        save_comparison = request.form.get('save_comparison', 'false').lower() == 'true'
        text_protection = request.form.get('text_protection', 'true').lower() == 'true'
        color_consistency = request.form.get('color_consistency', 'true').lower() == 'true'
        custom_prompt = request.form.get('prompt', '').strip()
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        temp_path = Path(OUTPUT_DIR) / 'temp' / filename
        temp_path.parent.mkdir(exist_ok=True, parents=True)
        file.save(temp_path)
        
        logger.info(f"File uploaded: {filename}")
        
        # Process in background thread
        def process_file():
            global is_processing
            is_processing = True
            
            try:
                emit_status('processing', f'Processing {filename}')
                
                col = get_colorizer()
                
                # Enable/disable text protection per request
                if not text_protection:
                    col.text_detector = None
                    logger.info("Text protection disabled for this request")
                else:
                    if col.text_detector is None:
                        try:
                            from .text_detector import TextDetector
                        except ImportError:
                            from backend.text_detector import TextDetector
                        col.text_detector = TextDetector()
                        logger.info("Text protection enabled")
                
                # Set custom prompt if provided
                if custom_prompt:
                    col.set_prompt(custom_prompt)
                
                # Ensure model is initialized
                if col.pipeline.pipeline is None:
                    emit_status('loading', 'Loading SD+ControlNet model...')
                    col.initialize_model()
                
                emit_status('processing', 'Colorizing...')
                
                # Check if it's a single image or batch
                is_zip = temp_path.suffix.lower() == '.zip'
                is_image = temp_path.suffix.lower() in SUPPORTED_FORMATS
                
                if is_zip or temp_path.is_dir():
                    # Batch processing
                    result = col.colorize_batch(
                        input_path=temp_path,
                        create_zip=create_zip,
                        enable_color_consistency=color_consistency,
                        progress_callback=emit_progress
                    )
                elif is_image:
                    # Single image
                    result = col.colorize_single_image(
                        image_path=temp_path,
                        save_comparison=save_comparison,
                        progress_callback=lambda p, s, t: emit_progress(s, t, filename)
                    )
                else:
                    result = {'success': False, 'error': 'Unsupported file type'}
                
                # Emit completion
                if result.get('success'):
                    emit_status('complete', 'Colorization complete!')
                    socketio.emit('complete', result)
                else:
                    emit_status('error', result.get('error', 'Unknown error'))
                    socketio.emit('error', result)
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                emit_status('error', str(e))
                socketio.emit('error', {'error': str(e)})
            
            finally:
                is_processing = False
                # Cleanup temp file
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                except:
                    pass
        
        # Start processing thread
        colorization_thread = threading.Thread(target=process_file)
        colorization_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Processing started'
        })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        is_processing = False
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/output/<path:filename>', methods=['GET'])
def get_output_file(filename):
    """Serve output files."""
    try:
        return send_from_directory(OUTPUT_DIR, filename)
    except Exception as e:
        logger.error(f"Failed to serve file: {e}")
        return jsonify({
            'success': False,
            'error': 'File not found'
        }), 404


@app.route('/api/cancel', methods=['POST'])
def cancel_processing():
    """Cancel current processing (not fully implemented)."""
    global is_processing
    
    # Note: This is a simplified cancellation
    # Full implementation would need proper thread management
    is_processing = False
    emit_status('cancelled', 'Processing cancelled')
    
    return jsonify({
        'success': True,
        'message': 'Cancellation requested'
    })


# WebSocket Events

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


@socketio.on('ping')
def handle_ping():
    """Handle ping from client."""
    emit('pong', {'timestamp': os.times().elapsed})


@socketio.on('download_models')
def download_models_handler(data):
    """Download models with progress updates via WebSocket."""
    try:
        model_name = data.get('model', 'anythingv5')
        logger.info(f"Starting model download: {model_name}")
        
        socketio.emit('download_status', {
            'status': 'started',
            'message': f'Starting download of {model_name}...'
        })
        
        # Get or create colorizer (this will trigger model downloads if needed)
        col = get_colorizer()
        
        # Initialize the model (this downloads if not present)
        col.initialize_model(model_name)
        
        socketio.emit('download_complete', {
            'success': True,
            'message': 'Models ready for colorization'
        })
        logger.info("Models ready")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Model download error: {e}")
        socketio.emit('download_error', {
            'success': False,
            'error': error_msg
        })


# Health check
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


def run_server(host: str = FLASK_HOST, port: int = FLASK_PORT, debug: bool = False):
    """
    Run the Flask server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    logger.info(f"Starting server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server()
