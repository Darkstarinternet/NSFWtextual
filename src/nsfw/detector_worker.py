import sys
import json
from nudenet import NudeDetector

def main():
    detector = None
    try:
        sys.stderr.write("NudeDetector: Initializing...\n")
        sys.stderr.flush()
        detector = NudeDetector()
        sys.stderr.write("NudeDetector: Initialization complete.\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"Error initializing NudeDetector: {e}\n")
        sys.stderr.flush()
        sys.exit(1)
    for line in sys.stdin:
        image_path = line.strip()
        if image_path == "STOP":
            break
        try:
            sys.stderr.write(f"Processing image: {image_path}\n")
            sys.stderr.flush()
            result = detector.detect(image_path)
            if result:
                sys.stdout.write(json.dumps({"path": image_path, "labels": result, "status": "nsfw_detected"}) + "\n")
            else:
                sys.stdout.write(json.dumps({"path": image_path, "labels": [], "status": "processed"}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error processing {image_path}: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
