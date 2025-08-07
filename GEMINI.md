# Project Overview for Gemini CLI Agent

This document provides essential context for the Gemini CLI agent to effectively interact with and manage this project.

## Project Type
This is a terminal user interface (TUI) that uses Textual.

## Project descriptions
This project should display a Textual (https://textual.textualize.io/) terminal user interface allowing the user to 
scan a directory for any images that are not safe for work (NSFW). A root directory should be able to be selected in 
the TUI, defaulting to "/Users/Tom/Websites/beddev". There should be a "Scan" button that performs the scan on the 
selected directory structure searching for all image files. For each image file that is NSFW print a line to a results 
log field in the TUI giving the full path of the image file and the labels for that image.

## Key Technologies
- **Frontend Framework:** Textual
- **Use NudeNet (https://github.com/notAI-tech/NudeNet) for testing of NSFW images
- 
## Project Structure
- `src/`: Contains the main application source code.

## Styling Conventions
- The project uses the Dracula theme color palette for its dark theme.
  - Background: `#282a36`
  - Foreground: `#f8f8f2`
  - Link Color: `#ff79c6`
- Add descriptive docstrings to all classes and functions

## Notes for Agent
- Use the Dracula theme color scheme for consistency.
- When using the "replace" tool, reload the file and reexamine the code before making the replacement.
- Do not offer to run PyLint or other linting tools
