import sys
import json
from nudenet import NudeDetector

def main():
    detector = NudeDetector()
    for line in sys.stdin:
        image_path = line.strip()
        if image_path == "STOP":
            break
        try:
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
