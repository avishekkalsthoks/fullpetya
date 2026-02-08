#!/usr/bin/env python3
"""
Online Face Enrollment Tool for Smart Vision Guide
Registers faces directly to the cloud API using the Pi camera.
"""

import time
import argparse
import sys
from handlers.camera_handler import CameraHandler
from handlers.face_recognition_handler import FaceRecognitionHandler

def main():
    parser = argparse.ArgumentParser(description="Enroll faces for Online Smart Vision Guide")
    parser.add_argument("name", help="Name of the person to enroll")
    parser.add_argument("--train", action="store_true", help="Capture 5 images for better accuracy (recommended)")
    args = parser.parse_args()

    name = args.name.strip()
    if not name:
        print("Error: Name cannot be empty.")
        return

    print(f"Initializing camera for {name}...")
    
    try:
        # Initialize handlers
        camera = CameraHandler()
        face_handler = FaceRecognitionHandler()
        
        # Check if cloud API is configured
        if not face_handler.cloud_api_url:
            print("❌ Error: FACE_API_URL is not configured in .env")
            print("   Please set your Codespaces URL first.")
            return

        # Test connection
        print("Testing cloud connection...")
        success, msg = face_handler.test_cloud_connection()
        if not success:
            print(f"❌ Connection failed: {msg}")
            return
        print(f"✅ {msg}")

        if args.train:
            # Training mode (5 images)
            print(f"\n🎓 Training mode for '{name}'")
            print("We will capture 5 images. Please move your head slightly between shots.")
            print("1. Front view")
            print("2. Slight left")
            print("3. Slight right")
            print("4. Slight up")
            print("5. Slight down")
            
            images = []
            for i in range(5):
                print(f"\n📸 Capture {i+1}/5 - Press ENTER to capture...", end="")
                input()
                print("   Capturing...", end="", flush=True)
                
                img_bytes = camera.capture_image_bytes()
                if not img_bytes:
                    print("❌ Failed to capture image.")
                    continue
                    
                images.append(img_bytes)
                print(" Done!")
                time.sleep(1)

            if not images:
                print("❌ No images captured.")
                return

            print(f"\n☁️  Uploading {len(images)} images for training...")
            success, msg = face_handler.train_cloud(images, name)
            
            if success:
                print(f"✅ Success: {msg}")
            else:
                print(f"❌ Failed: {msg}")

        else:
            # Quick registration (1 image)
            print(f"\n📸 Quick registration for '{name}'")
            print("Position face in front of camera and press ENTER...", end="")
            input()
            
            print("   Capturing...", end="", flush=True)
            img_bytes = camera.capture_image_bytes()
            
            if not img_bytes:
                print("❌ Failed to capture image.")
                return
            print(" Done!")

            print(f"☁️  Registering '{name}'...")
            success, msg = face_handler.register_cloud(img_bytes, name)
            
            if success:
                print(f"✅ Success: {msg}")
            else:
                print(f"❌ Failed: {msg}")

        # Show updated list
        print("\n📋 Currently registered people:")
        people = face_handler.get_enrolled_people()
        if people:
            print(", ".join(people))
        else:
            print("(None)")

    except KeyboardInterrupt:
        print("\n👋 Enrollment cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if 'camera' in locals():
            camera.stop()

if __name__ == "__main__":
    main()
