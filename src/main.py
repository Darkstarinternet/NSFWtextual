
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Button, RichLog, Static
from textual.binding import Binding
from rich.text import Text
from nudenet import NudeDetector
import os
import time
from textual import work


class NSFWScanner(App):
    """A Textual app to scan a directory for NSFW images."""

    BINDINGS = [
        Binding("q", "quit", "Quit", key_display="Q"),
    ]

    CSS_PATH = "tcss/main.tcss"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detector = NudeDetector()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="results-container"):
            yield Static(f"Scanning directory: /Users/Tom/Websites/beddev", id="scan-directory")
            yield Button("Scan", id="scan", variant="primary")
            with Container(id="stats-line"):
                yield Static("Images scanned: 0", id="scan-count")
                yield Static("Time elapsed: 00:00:00", id="scan-timer")
            yield RichLog(id="results", wrap=True)
        yield Footer()
        

    

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "scan":
            self.scan_directory()

    def action_quit(self) -> None:
        """Called in response to key binding."""
        self.exit()

    @work(exclusive=True, thread=True)
    def scan_directory(self) -> None:
        """Scans the selected directory for NSFW images."""
        results_log = self.query_one("#results")
        scan_count_display = self.query_one("#scan-count", Static)
        scan_timer_display = self.query_one("#scan-timer", Static)

        results_log.clear()
        results_log.write("Starting scan...")
        found_nsfw = False
        scanned_images = 0
        start_time = time.time()

        def update_timer():
            elapsed_time = time.time() - start_time
            hours, rem = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(rem, 60)
            scan_timer_display.update(f"Time elapsed: {int(hours):02}:{int(minutes):02}:{int(seconds):02}")

        timer_id = self.set_interval(1, update_timer)

        for root, _, files in os.walk("/Users/Tom/Websites/beddev"):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                    image_path = os.path.join(root, file)
                    scanned_images += 1
                    scan_count_display.update(f"Images scanned: {scanned_images}")
                    try:
                        result = self.detector.detect(image_path)
                        if result:
                            labels = ", ".join([d["class"] for d in result])
                            results_log.write(f"NSFW: {image_path} - Labels: {labels}")
                            found_nsfw = True
                    except Exception as e:
                        results_log.write(
                            f"Error processing {image_path}: {e}"
                        )
        if not found_nsfw:
            results_log.write("No NSFW images found.")
        results_log.write("Scan complete.")
        self.call_from_thread(lambda: self.clear_interval(timer_id))


if __name__ == "__main__":
    app = NSFWScanner()
    app.run()
