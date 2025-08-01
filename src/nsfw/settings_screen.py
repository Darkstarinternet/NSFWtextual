from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Checkbox, Label
from textual.containers import Vertical, Horizontal

class SettingsScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None, *, initial_labels: set[str]):
        super().__init__(name=name, id=id, classes=classes)
        self.initial_labels = initial_labels
        self.selected_labels = set(initial_labels) # Copy for modification

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="settings-container"):
            yield Label("Toggle NudeNet Labels:", classes="settings-title")
            
            # Common NudeNet labels
            labels = ["female_genitalia", "male_genitalia", "buttocks", "female_breast", "anus", "face"]

            for label in labels:
                checkbox = Checkbox(label.replace("_", " ").title(), value=label in self.initial_labels, id=f"checkbox_{label}")
                yield checkbox
            
            with Horizontal(classes="settings-buttons"):
                yield Button("Save", id="save_settings", variant="primary")
                yield Button("Cancel", id="cancel_settings")
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        label_id = event.control.id.replace("checkbox_", "")
        if event.value:
            self.selected_labels.add(label_id)
        else:
            self.selected_labels.discard(label_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_settings":
            self.dismiss(self.selected_labels) # Dismiss with the new selections
        elif event.button.id == "cancel_settings":
            self.dismiss(self.initial_labels) # Dismiss with original selections
