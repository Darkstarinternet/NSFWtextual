from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Checkbox, Label
from textual.containers import Vertical, Horizontal, ScrollableContainer

class SettingsScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None, *, initial_labels: set[str]):
        super().__init__(name=name, id=id, classes=classes)
        self.initial_labels = initial_labels
        self.selected_labels = set(initial_labels) # Copy for modification
        # Create a mapping from safe IDs to actual labels
        self.id_to_label = {}
        self.label_to_id = {}

    def _make_safe_id(self, label: str) -> str:
        """Convert a label to a safe ID by replacing spaces with underscores."""
        return label.replace(" ", "_").replace("-", "_")

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="settings-container"):
            yield Label("Toggle NudeNet Labels:", classes="settings-title")

            # Group labels by category for better organization
            categories = {
                "Face": ["female face", "male face"],
                "Upper Body": ["breast", "exposed breast", "exposed breasts", "male breast", "exposed armpits"],
                "Midsection": ["belly", "exposed belly"],
                "Lower Body": ["buttocks", "exposed buttocks", "vagina", "exposed vagina", "exposed penis", "exposed anus"],
                "Extremities": ["feet", "exposed feet"]
            }

            # Display checkboxes grouped by category
            for category, category_labels in categories.items():
                yield Label(f"--- {category} ---", classes="category-header")

                # Create a horizontal container for checkboxes in this category
                with Horizontal(classes="checkbox-row"):
                    for label in category_labels:
                        # Create a safe ID for the checkbox
                        safe_id = self._make_safe_id(label)
                        self.id_to_label[safe_id] = label
                        self.label_to_id[label] = safe_id

                        checkbox = Checkbox(
                            label.title(), 
                            value=label in self.initial_labels, 
                            id=f"checkbox_{safe_id}"
                        )
                        yield checkbox

            with Horizontal(classes="settings-buttons"):
                yield Button("Select All", id="select_all", variant="default")
                yield Button("Clear All", id="clear_all", variant="default")
                yield Button("Save", id="save_settings", variant="primary")
                yield Button("Cancel", id="cancel_settings")
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        # Get the checkbox ID and convert back to the original label
        checkbox_id = event.control.id.replace("checkbox_", "")
        label = self.id_to_label.get(checkbox_id)

        if label:
            if event.value:
                self.selected_labels.add(label)
            else:
                self.selected_labels.discard(label)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_settings":
            self.dismiss(self.selected_labels) # Dismiss with the new selections
        elif event.button.id == "cancel_settings":
            self.dismiss(self.initial_labels) # Dismiss with original selections
        elif event.button.id == "select_all":
            # Select all checkboxes
            for checkbox in self.query(Checkbox):
                checkbox.value = True
        elif event.button.id == "clear_all":
            # Clear all checkboxes
            for checkbox in self.query(Checkbox):
                checkbox.value = False
