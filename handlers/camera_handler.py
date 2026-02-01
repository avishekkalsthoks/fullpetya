"""
Camera Handler for Smart Vision Guide
Optimized for Raspberry Pi Zero 2W with enhanced warmup and retry logic.
"""

import cv2
import tempfile
import os
import time


class CameraHandler:
    """Handler for camera operations with Pi Zero 2W optimizations."""
    
    def __init__(self, width=512, height=384, device=0, warmup_frames=10, retry_attempts=3):
        """
        Initialize camera handler.
        
        Args:
            width: Image width (reduced from 640 for faster processing)
            height: Image height
            device: Camera device index
            warmup_frames: Number of frames to capture for camera warmup
            retry_attempts: Number of retry attempts for camera initialization
        """
        self.width = width
        self.height = height
        self.device = device
        self.warmup_frames = warmup_frames
        self.retry_attempts = retry_attempts
        self.cap = None

    def start(self):
        """Initialize the camera capture with retry logic."""
        if self.cap is not None:
            return
        
        for attempt in range(self.retry_attempts):
            try:
                self.cap = cv2.VideoCapture(self.device)
                
                if not self.cap.isOpened():
                    raise RuntimeError("Camera device not opened")
                
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                
                # Give camera time to initialize (critical for Pi Camera)
                time.sleep(0.8)
                
                # Test capture to ensure camera is working
                ret, _ = self.cap.read()
                if not ret:
                    raise RuntimeError("Camera test capture failed")
                
                print(f"✓ Camera initialized successfully")
                return
                
            except Exception as e:
                print(f"Camera init attempt {attempt + 1}/{self.retry_attempts} failed: {e}")
                if self.cap:
                    try:
                        self.cap.release()
                    except:
                        pass
                    self.cap = None
                
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)
                else:
                    raise RuntimeError(f"Failed to initialize camera after {self.retry_attempts} attempts")

    def stop(self):
        """Release the camera."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def capture_image_bytes(self, quality=70):
        """
        Capture an image and return as JPEG bytes.
        
        Args:
            quality: JPEG quality (0-100), reduced from 80 to 70 for smaller payloads
            
        Returns:
            JPEG image bytes
        """
        self.start()
        
        # Capture multiple frames to allow auto-exposure/white balance to adjust
        # Increased from 5 to warmup_frames for better Pi Camera stability
        frame = None
        successful_reads = 0
        
        for i in range(self.warmup_frames):
            ret, temp_frame = self.cap.read()
            if ret and temp_frame is not None:
                frame = temp_frame
                successful_reads += 1
            time.sleep(0.05)  # Small delay between frames

        if frame is None or successful_reads < 3:
            raise RuntimeError(f'Failed to capture image from camera (only {successful_reads}/{self.warmup_frames} successful reads)')

        # Encode as JPEG bytes
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ret, buf = cv2.imencode('.jpg', frame, encode_param)
        
        if not ret:
            raise RuntimeError('JPEG encode failed')
            
        jpeg_bytes = buf.tobytes()
        print(f"✓ Captured image: {len(jpeg_bytes)} bytes")
        return jpeg_bytes

    def capture_image_file(self, path=None, quality=70):
        """
        Capture an image and save to file.
        
        Args:
            path: Optional path to save image
            quality: JPEG quality (0-100)
            
        Returns:
            Path to saved image
        """
        data = self.capture_image_bytes(quality)
        if path is None:
            fd, path = tempfile.mkstemp(suffix='.jpg')
            os.close(fd)
        with open(path, 'wb') as f:
            f.write(data)
        return path
    
    def preview(self, duration_seconds=3):
        """
        Show a preview window (for testing on desktop).
        
        Args:
            duration_seconds: How long to show preview
        """
        self.start()
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            ret, frame = self.cap.read()
            if ret:
                cv2.imshow('Preview', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        cv2.destroyAllWindows()
    
    def get_camera_info(self):
        """Get camera information for debugging."""
        if self.cap is None:
            return "Camera not initialized"
        
        info = {
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': int(self.cap.get(cv2.CAP_PROP_FPS)),
            'backend': self.cap.getBackendName()
        }
        return info
