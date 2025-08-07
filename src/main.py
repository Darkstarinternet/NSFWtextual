import multiprocessing

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Button, RichLog, Static
from textual.binding import Binding
from textual import on
from textual import work

import os
import time
import platform
import pyperclip
import subprocess
import json
import threading
import queue
from nsfw.settings_screen import SettingsScreen


def _reader_thread(pipe, q, stop_event):
    while not stop_event.is_set():
        line = pipe.readline()
        if line:
            q.put(line)
        else:
            # If there's no line and the process is done, break
            if pipe.closed or pipe.poll() is not None:
                break
        time.sleep(0.01) # Prevent busy-waiting
    pipe.close()


class NSFWScanner(App):
    """A Textual app to scan a directory for NSFW images."""

    SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/100x150"     # 528 in 38 sec - # 1 min 14 sec
    # SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/150x225"
    # SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/250x375"   # 302 in 16-17 sec
    # SCAN_DIRECTORY = "/Users/Tom/Projects/Python/NSFW/images/1200x1200" # 599 in 1 min 17 sec
    # SCAN_DIRECTORY = "/Users/Tom/Websites/beddev/sites/default/files/escort-photos/Marlene"
    # SCAN_DIRECTORY = "/Users/Tom/Websites/beddev/sites/default/files/styles/image_widget_crop_100x150"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", key_display="^q"),
        Binding("s", "show_settings", "Settings", key_display="S"),
    ]

    ENABLE_COMMAND_PALETTE = False

    # All possible labels from NudeNet default faster model
    NUDENET_DEFAULT_LABELS = {
        "exposed anus", "exposed armpits", "belly", "exposed belly", "buttocks", "exposed buttocks", "female face",
        "male face", "feet", "exposed feet", "breast", "exposed breast", "vagina", "exposed vagina", "male breast",
        "exposed penis"
    }

    # All possible labels from NudeNet base more accurate model
    NUDENET_BASE_LABELS = {
        "exposed belly", "exposed buttocks", "exposed breasts", "exposed vagina", "exposed penis", "male breast"
    }

    # Use all labels from the default NudeNet model by default
    DEFAULT_LABELS = NUDENET_DEFAULT_LABELS.copy()

    SCREENS = {"settings": SettingsScreen}

    CSS_PATH = "nsfw/tcss/main.tcss"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.worker_process = None # Initialize worker_process to None
        self.selected_labels = set(self.DEFAULT_LABELS) # Initialize with default labels
        self.current_model = "default" # Default NudeNet model
        self.scanning = False # Flag to indicate if scanning is in progress
        self.stop_event = threading.Event() # Event to signal stopping of scan
        self.results_log = None # Initialize results log
        self.notification_log = None # Initialize notification log

    def on_mount(self) -> None:
        self.results_log = self.query_one("#results-widget", RichLog)
        self.notification_log = self.query_one("#notifications-widget", RichLog)
        self.notification_log.write(f"[bold blue]Initialized with NudeNet Model:[/bold blue] [green]{self.current_model.title()}[/green]")
        self.notification_log.write(f"[bold blue]Selected Labels:[/bold blue] [green]{sorted(list(self.selected_labels))}[/green]")


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="results-container"):
            yield Static(f"Scanning directory: {self.SCAN_DIRECTORY}", id="scan-directory")
            with Horizontal(id="scan-buttons"):
                yield Button("Scan", id="scan", variant="primary")
                yield Button("Stop", id="stop", variant="default")
            with Container(id="stats-line"):
                yield Static("Images scanned: 0", id="scan-count")
                yield Static("Time elapsed: 00:00:00", id="scan-timer")
            results_widet = RichLog(id="results-widget", wrap=True, markup=True, highlight=True)
            results_widet.border_title = "Results"
            yield results_widet
            notifications_widget = RichLog(id="notifications-widget", wrap=True, auto_scroll=True, markup=True)
            notifications_widget.border_title = "Notifications"
            yield notifications_widget
        yield Footer()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "scan":
            self.results_log.clear()
            self.notification_log.clear()
            self.scanning = True
            self.stop_event.clear() # Clear the stop event for a new scan
            self.scan_directory()
        elif event.button.id == "stop":
            self.scanning = False
            self.stop_event.set() # Set the stop event to signal termination


    def handle_settings_result(self, result: tuple[set[str], str]) -> None:
        """Handle the result from the settings screen."""
        selected_labels, selected_model = result
        self.selected_labels = selected_labels
        self.current_model = selected_model
        self.query_one("#results-widget", RichLog).write(f"Selected NudeNet Model: {self.current_model.title()}")
        self.query_one("#results-widget", RichLog).write(f"Selected labels: {self.selected_labels}")


    def action_quit(self) -> None:
        """Called in response to key binding."""
        self.exit()

    def action_show_settings(self) -> None:
        """Show the settings screen."""
        self.app.push_screen(SettingsScreen(initial_labels=self.selected_labels, initial_model=self.current_model), self.handle_settings_result)

    def action_open_file(self, path: str) -> None:
        """Action to open a file using the system's default application."""
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path], check=True)
            elif platform.system() == "Windows":
                os.startfile(path)
            else:  # Linux
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            self.notification_log.write(f"Error opening file {path}: {e}")

    def action_copy_to_clipboard(self, text: str) -> None:
        """Action to copy text to clipboard."""
        try:
            pyperclip.copy(text)
            self.notification_log.write(f"Copied to clipboard: {text}")
        except Exception as e:
            self.notification_log.write(f"Error copying to clipboard: {e}")


    @work(exclusive=True, thread=True)
    def scan_directory(self) -> None:
        """Scans the selected directory for NSFW images."""
        results_log = self.query_one("#results-widget", RichLog)
        notification_log = self.query_one("#notifications-widget", RichLog)
        scan_count_display = self.query_one("#scan-count", Static)
        scan_timer_display = self.query_one("#scan-timer", Static)

        results_log.clear()
        notification_log.write("[bold blue]Loading NSFW detector...[/bold blue]")
        notification_log.write(f"[bold blue]NudeNet Model:[/bold blue] [green]{self.current_model.title()}[/green]")

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

        stdout_thread = threading.Thread(target=_reader_thread, args=(self.worker_process.stdout, stdout_queue, self.stop_event), daemon=True)
        stderr_thread = threading.Thread(target=_reader_thread, args=(self.worker_process.stderr, stderr_queue, self.stop_event), daemon=True)

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
            if not self.scanning: # Check if stop button was pressed
                break
            self.worker_process.stdin.write(image_path + "\n")
        self.worker_process.stdin.write("STOP\n") # Sentinel to stop the worker
        self.worker_process.stdin.flush() # Ensure all data is sent
        self.worker_process.stdin.close()

        # Read results from the worker and errors from stderr
        # The main loop will continuously check queues for updates
        while self.scanning and (self.worker_process.poll() is None or not stdout_queue.empty() or not stderr_queue.empty()):
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
                                self.call_from_thread(lambda p=image_path, d=image_path_display, l=labels: 
                                    results_log.write(f"NSFW: [@click=app.copy_to_clipboard('{p}')]📋[/] [@click=app.open_file('{p}')]{d}[/] - Labels: {l}"))
                                found_nsfw = True
                            else:
                                # NSFW detected but not in selected labels, still processed
                                image_path_display = image_path.replace(os.path.expanduser("~"), "~")
                                self.call_from_thread(lambda p=image_path, d=image_path_display: 
                                    results_log.write(f"[@click=app.copy_to_clipboard('{p}')]📋[/] [@click=app.open_file('{p}')]{d}[/]"))
                        elif data.get("status") == "processed":
                            image_path_display = image_path.replace(os.path.expanduser("~"), "~")
                            self.call_from_thread(lambda p=image_path, d=image_path_display: 
                                results_log.write(f"[@click=app.copy_to_clipboard('{p}')]📋[/] [@click=app.open_file('{p}')]{d}[/]"))

                    except json.JSONDecodeError:
                        self.call_from_thread(lambda: self.notification_log.write(f"Error decoding JSON from worker stdout: {stdout_line.strip()}"))
                    except Exception as e:
                        self.call_from_thread(lambda: self.notification_log.write(f"Error processing worker stdout: {e}"))
            except queue.Empty:
                pass

            # Read from stderr
            try:
                stderr_line = stderr_queue.get_nowait()
                if stderr_line:
                    self.call_from_thread(lambda: self.notification_log.write(f"{stderr_line.strip()}"))
            except queue.Empty:
                pass

            # Small sleep to prevent busy-waiting
            time.sleep(0.01)

        # Ensure all threads are joined and the process is waited for after loop breaks
        if self.worker_process and self.worker_process.poll() is None:
            self.worker_process.terminate() # Terminate the worker process if it's still running
            self.worker_process.wait()

        stdout_thread.join()
        stderr_thread.join()

        if not found_nsfw:
            self.call_from_thread(lambda: self.notification_log.write("No NSFW images found."))
        self.call_from_thread(lambda: self.notification_log.write("Scan complete."))
        self.call_from_thread(lambda: timer_object.stop())
        self.scanning = False # Reset scanning flag


if __name__ == "__main__":
    app = NSFWScanner()
    app.run()
