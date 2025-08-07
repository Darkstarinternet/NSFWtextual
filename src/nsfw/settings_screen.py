from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Checkbox, Label, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer, Container
from textual.reactive import reactive

class SettingsScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    # Reactive property to track screen size
    checkboxes_per_row = reactive(4)

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None, *, initial_labels: set[str]):
        super().__init__(name=name, id=id, classes=classes)
        self.initial_labels = initial_labels
        self.selected_labels = set(initial_labels) # Copy for modification
        # Create a mapping from safe IDs to actual labels
        self.id_to_label = {}
        self.label_to_id = {}

    def on_resize(self) -> None:
        """Handle terminal resize events to adjust layout."""
        # Get the current width
        width = self.size.width

        # Adjust checkboxes per row based on width
        if width < 80:  # Narrow screens
            self.checkboxes_per_row = 2
        elif width < 120:  # Medium screens
            self.checkboxes_per_row = 3
        else:  # Wide screens
            self.checkboxes_per_row = 4

    def _make_safe_id(self, label: str) -> str:
        """Convert a label to a safe ID by replacing spaces with underscores."""
        return label.replace(" ", "_").replace("-", "_")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # Scrollable container for checkboxes
        with ScrollableContainer(id="checkboxes-container"):
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

                # Create checkboxes in batches based on screen width
                checkbox_batch = []
                for i, label in enumerate(category_labels):
                    # Create a safe ID for the checkbox
                    safe_id = self._make_safe_id(label)
                    self.id_to_label[safe_id] = label
                    self.label_to_id[label] = safe_id

                    checkbox = Checkbox(
                        label.title(), 
                        value=label in self.initial_labels, 
                        id=f"checkbox_{safe_id}"
                    )
                    checkbox_batch.append(checkbox)

                    # Create a new row based on the dynamic checkboxes_per_row value
                    if (i + 1) % self.checkboxes_per_row == 0 or i == len(category_labels) - 1:
                        row_class = "checkbox-row"
                        if i == len(category_labels) - 1 and len(checkbox_batch) < self.checkboxes_per_row:
                            row_class = f"checkbox-row checkbox-row-{len(checkbox_batch)}"

                        with Horizontal(classes=row_class):
                            for cb in checkbox_batch:
                                yield cb
                        checkbox_batch = []

        # Container for buttons
        with Container(id="buttons-container"):
            with Horizontal(classes="button-row"):
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
