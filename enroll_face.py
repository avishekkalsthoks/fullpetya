"""
Face Enrollment Script for Local Face Recognition
Creates folder-based face database for OpenCV LBPH recognition.
NO dlib required - uses OpenCV Haar cascade for face detection.
"""

import os
import sys
import argparse
import cv2
from handlers.camera_handler import CameraHandler


# Haar cascade for face detection
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def detect_faces(image_path):
    """Detect faces in an image using OpenCV Haar cascade."""
    image = cv2.imread(image_path)
    if image is None:
        return []
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    return faces


def create_person_folder(faces_dir, person_name):
    """Create a folder for a person if it doesn't exist."""
    person_path = os.path.join(faces_dir, person_name)
    if not os.path.exists(person_path):
        os.makedirs(person_path)
        print(f"✓ Created folder: {person_path}")
    return person_path


def enroll_from_camera(person_name, faces_dir="faces", num_photos=3):
    """
    Enroll a person by capturing photos from camera.
    
    Args:
        person_name: Name of the person to enroll
        faces_dir: Face database directory
        num_photos: Number of photos to capture (recommended: 3-5)
    """
    print(f"\n📷 Enrolling {person_name} ({num_photos} photos)")
    print("=" * 50)
    
    # Create person folder
    person_path = create_person_folder(faces_dir, person_name)
    
    # Initialize camera
    camera = CameraHandler()
    camera.start()
    
    enrolled_count = 0
    
    for i in range(num_photos):
        input(f"\n[{i+1}/{num_photos}] Press Enter to capture photo {i+1}...")
        
        try:
            # Capture image
            print("  Capturing...")
            image_bytes = camera.capture_image_bytes()
            
            # Save temporarily to verify face
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                tmp.write(image_bytes)
                temp_path = tmp.name
            
            # Verify face is detected using OpenCV
            face_locations = detect_faces(temp_path)
            
            if len(face_locations) == 0:
                print("  ✗ No face detected. Please try again.")
                os.remove(temp_path)
                continue
            
            if len(face_locations) > 1:
                print(f"  ⚠️  {len(face_locations)} faces detected. Please ensure only one person is in frame.")
                retry = input("  Use this image anyway? (y/n): ")
                if retry.lower() != 'y':
                    os.remove(temp_path)
                    continue
            
            # Save to person folder
            image_name = f"img{enrolled_count + 1}.jpg"
            final_path = os.path.join(person_path, image_name)
            
            # Move temp file to final location
            import shutil
            shutil.move(temp_path, final_path)
            
            enrolled_count += 1
            print(f"  ✓ Saved {image_name}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    camera.stop()
    
    print("\n" + "=" * 50)
    print(f"✓ Enrollment complete: {enrolled_count}/{num_photos} photos saved")
    
    if enrolled_count < num_photos:
        retry = input("\nWant to capture more photos? (y/n): ")
        if retry.lower() == 'y':
            additional = int(input("How many more? "))
            enroll_from_camera(person_name, faces_dir, additional)


def enroll_from_image(person_name, image_path, faces_dir="faces"):
    """
    Enroll a person from an existing image file.
    
    Args:
        person_name: Name of the person
        image_path: Path to image file
        faces_dir: Face database directory
    """
    print(f"\n📷 Enrolling {person_name} from image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"✗ Image not found: {image_path}")
        return False
    
    # Create person folder
    person_path = create_person_folder(faces_dir, person_name)
    
    try:
        # Verify face is detected using OpenCV
        face_locations = detect_faces(image_path)
        
        if len(face_locations) == 0:
            print("✗ No face detected in image")
            return False
        
        if len(face_locations) > 1:
            print(f"⚠️  {len(face_locations)} faces detected (will use first one)")
        
        # Copy image to person folder
        import shutil
        existing_count = len([f for f in os.listdir(person_path) if f.endswith(('.jpg', '.jpeg', '.png'))])
        image_name = f"img{existing_count + 1}.jpg"
        final_path = os.path.join(person_path, image_name)
        
        shutil.copy(image_path, final_path)
        
        print(f"✓ Enrolled {person_name}: {image_name}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def list_enrolled(faces_dir="faces"):
    """List all enrolled people."""
    print("\n👥 Enrolled People")
    print("=" * 50)
    
    if not os.path.exists(faces_dir):
        print(f"Face database not found: {faces_dir}")
        return
    
    people = []
    for person_name in os.listdir(faces_dir):
        person_path = os.path.join(faces_dir, person_name)
        if os.path.isdir(person_path):
            images = [f for f in os.listdir(person_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
            people.append((person_name, len(images)))
    
    if not people:
        print("No people enrolled yet.")
        return
    
    for name, count in sorted(people):
        print(f"  • {name}: {count} image(s)")
    
    print(f"\nTotal: {len(people)} people, {sum(c for _, c in people)} images")


def remove_person(person_name, faces_dir="faces"):
    """Remove a person from the face database."""
    person_path = os.path.join(faces_dir, person_name)
    
    if not os.path.exists(person_path):
        print(f"✗ Person not found: {person_name}")
        return False
    
    confirm = input(f"⚠️  Remove all images for '{person_name}'? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled")
        return False
    
    import shutil
    shutil.rmtree(person_path)
    print(f"✓ Removed {person_name}")
    return True


def main():
    """Main enrollment interface."""
    parser = argparse.ArgumentParser(description="Enroll faces for local face recognition (OpenCV LBPH)")
    parser.add_argument('name', nargs='?', help='Person name to enroll')
    parser.add_argument('--image', '-i', help='Path to existing image file')
    parser.add_argument('--photos', '-p', type=int, default=3, help='Number of photos to capture (default: 3)')
    parser.add_argument('--list', '-l', action='store_true', help='List enrolled people')
    parser.add_argument('--remove', '-r', metavar='NAME', help='Remove a person')
    parser.add_argument('--faces-dir', '-d', default='faces', help='Face database directory (default: faces)')
    
    args = parser.parse_args()
    
    # List mode
    if args.list:
        list_enrolled(args.faces_dir)
        return
    
    # Remove mode
    if args.remove:
        remove_person(args.remove, args.faces_dir)
        return
    
    # Enroll mode
    if not args.name:
        print("Error: Person name required")
        parser.print_help()
        return
    
    # Create faces directory if it doesn't exist
    if not os.path.exists(args.faces_dir):
        os.makedirs(args.faces_dir)
        print(f"✓ Created face database: {args.faces_dir}")
    
    # Enroll from image or camera
    if args.image:
        enroll_from_image(args.name, args.image, args.faces_dir)
    else:
        enroll_from_camera(args.name, args.faces_dir, args.photos)


if __name__ == '__main__':
    main()
