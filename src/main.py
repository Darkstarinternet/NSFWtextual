import multiprocessing
multiprocessing.set_start_method("spawn", force=True)

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Button, RichLog, Static
from textual.binding import Binding
import os
import time
from textual import work
import subprocess
import json
import threading
import queue
from nsfw.settings_screen import SettingsScreen


def _reader_thread(pipe, q):
    for line in iter(pipe.readline, ''):
        q.put(line)
    pipe.close()


class NSFWScanner(App):
    """A Textual app to scan a directory for NSFW images."""

    # SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/100x150"
    # SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/150x225"
    SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/250x375" # 302 ~ 17 sec
    # SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/1200x1200" # 599 @ 1 min 17 sec
    # SCAN_DIRECTORY = "/Users/Tom/Websites/beddev/sites/default/files/escort-photos/Marlene"
    # SCAN_DIRECTORY = "/Users/Tom/Websites/beddev/sites/default/files/styles/image_widget_crop_100x150"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", key_display="^q"),
        Binding("s", "show_settings", "Settings", key_display="S"),
    ]

    ENABLE_COMMAND_PALETTE = False

    DEFAULT_LABELS = {"female_genitalia", "male_genitalia", "buttocks", "female_breast", "anus", "face"}

    SCREENS = {"settings": SettingsScreen}

    CSS_PATH = "nsfw/tcss/main.tcss"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.worker_process = None # Initialize worker_process to None
        self.selected_labels = set(self.DEFAULT_LABELS) # Initialize with default labels

    def on_mount(self) -> None:
        pass


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="results-container"):
            yield Static(f"Scanning directory: {self.SCAN_DIRECTORY}", id="scan-directory")
            yield Button("Scan", id="scan", variant="primary")
            with Container(id="stats-line"):
                yield Static("Images scanned: 0", id="scan-count")
                yield Static("Time elapsed: 00:00:00", id="scan-timer")
            yield RichLog(id="results", wrap=True)
            yield RichLog(id="error-log", wrap=True, auto_scroll=True)
        yield Footer()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "scan":
            self.query_one("#results", RichLog).clear()
            self.query_one("#error-log", RichLog).clear()
            self.scan_directory()


    def handle_settings_result(self, selected_labels: set[str]) -> None:
        """Handle the result from the settings screen."""
        self.selected_labels = selected_labels
        self.query_one("#results", RichLog).write(f"Selected labels: {self.selected_labels}")


    def action_quit(self) -> None:
        """Called in response to key binding."""
        self.exit()

    def action_show_settings(self) -> None:
        """Show the settings screen."""
        self.app.push_screen(SettingsScreen(initial_labels=self.selected_labels), self.handle_settings_result)


    @work(exclusive=True, thread=True)
    def scan_directory(self) -> None:
        """Scans the selected directory for NSFW images."""
        results_log = self.query_one("#results", RichLog)
        error_log = self.query_one("#error-log", RichLog)
        scan_count_display = self.query_one("#scan-count", Static)
        scan_timer_display = self.query_one("#scan-timer", Static)

        results_log.clear()
        results_log.write("Loading detector...")
        found_nsfw = False
        scanned_images = 0
        start_time = time.time()

        def update_timer():
            elapsed_time = time.time() - start_time
            hours, rem = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(rem, 60)
            scan_timer_display.update(f"Time elapsed: {int(hours):02}:{int(minutes):02}:{int(seconds):02}")

        timer_object = self.call_from_thread(lambda: self.set_interval(1, update_timer))

        # Start the detector worker subprocess
        worker_path = os.path.join(os.path.dirname(__file__), "nsfw", "detector_worker.py")
        self.worker_process = subprocess.Popen(
            ["python", worker_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # Re-enable stderr redirection
            text=True,
            bufsize=1, # Line-buffered
        )

        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()

        stdout_thread = threading.Thread(target=_reader_thread, args=(self.worker_process.stdout, stdout_queue), daemon=True)
        stderr_thread = threading.Thread(target=_reader_thread, args=(self.worker_process.stderr, stderr_queue), daemon=True)

        stdout_thread.start()
        stderr_thread.start()

        all_image_paths = []
        directories = []
        for root, dirs, files in os.walk(self.SCAN_DIRECTORY):
            directories.append(root)

        directories.sort() # Sort directories alphabetically

        for root in directories:
            files_in_dir = []
            for file in os.listdir(root):
                full_path = os.path.join(root, file)
                if os.path.isfile(full_path) and file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                    files_in_dir.append(full_path)
            files_in_dir.sort() # Sort files within each directory
            all_image_paths.extend(files_in_dir)

        # Send image paths to the worker
        for image_path in all_image_paths:
            self.worker_process.stdin.write(image_path + "\n")
        self.worker_process.stdin.write("STOP\n") # Sentinel to stop the worker
        self.worker_process.stdin.flush() # Ensure all data is sent
        self.worker_process.stdin.close()

        # Read results from the worker and errors from stderr
        # The main loop will continuously check queues for updates
        while self.worker_process.poll() is None or not stdout_queue.empty() or not stderr_queue.empty():
            # Read from stdout
            try:
                stdout_line = stdout_queue.get_nowait()
                if stdout_line:
                    try:
                        data = json.loads(stdout_line.strip())
                        image_path = data["path"] # Define image_path here
                        # Always increment scanned_images for each processed image
                        scanned_images += 1
                        self.call_from_thread(lambda: scan_count_display.update(f"Images scanned: {scanned_images}"))

                        if data.get("status") == "nsfw_detected" and data.get("labels"):
                            # Filter based on selected labels
                            detected_labels = {d["class"] for d in data["labels"]}
                            if any(label in self.selected_labels for label in detected_labels):
                                labels = ", ".join([d["class"] for d in data["labels"]])
                                image_path_display = image_path.replace(os.path.expanduser("~"), "~")
                                self.call_from_thread(lambda: results_log.write(f"NSFW: {image_path_display} - Labels: {labels}"))
                                found_nsfw = True
                            else:
                                # NSFW detected but not in selected labels, still processed
                                image_path_display = image_path.replace(os.path.expanduser("~"), "~")
                                self.call_from_thread(lambda: results_log.write(f"{image_path_display}"))
                        elif data.get("status") == "processed":
                            image_path_display = image_path.replace(os.path.expanduser("~"), "~")
                            self.call_from_thread(lambda: results_log.write(f"{image_path_display}"))

                    except json.JSONDecodeError:
                        self.call_from_thread(lambda: error_log.write(f"Error decoding JSON from worker stdout: {stdout_line.strip()}"))
                    except Exception as e:
                        self.call_from_thread(lambda: error_log.write(f"Error processing worker stdout: {e}"))
            except queue.Empty:
                pass

            # Read from stderr
            try:
                stderr_line = stderr_queue.get_nowait()
                if stderr_line:
                    self.call_from_thread(lambda: error_log.write(f"{stderr_line.strip()}"))
            except queue.Empty:
                pass

            # Small sleep to prevent busy-waiting
            time.sleep(0.01)

        # Ensure all threads are joined and the process is waited for after loop breaks
        stdout_thread.join()
        stderr_thread.join()
        self.worker_process.wait() # Final wait to ensure the process is truly finished

        if not found_nsfw:
            self.call_from_thread(lambda: results_log.write("No NSFW images found."))
        self.call_from_thread(lambda: results_log.write("Scan complete."))
        self.call_from_thread(lambda: timer_object.stop())


if __name__ == "__main__":
    app = NSFWScanner()
    app.run()
