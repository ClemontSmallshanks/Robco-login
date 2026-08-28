# RobCo Terminal Visual Analysis

Based on the provided references (`spotify.png`, `Trespasser_screen.png`, `wordchoice.png`), the core visual identity of the RobCo terminal requires a strict departure from conventional GUI paradigms.

## 1. Composition and Layout
*   **The Terminal Viewport**: The content does not span the entire monitor. It is contained within a specific, narrower column or block, flanked by significant empty dark space. The empty space is not "wasted UI"; it represents the unlit phosphor of the physical CRT screen.
*   **Asymmetry**: Content is often left-aligned or clustered into specific blocks rather than being symmetrically centered across the entire screen.
*   **Information Density**: Text is much smaller than modern UI headers. The screen can fit many rows (e.g., 40+ rows) and columns (e.g., 80-120 columns) of data.

## 2. The Character Grid
*   **Absolute Grid Constraint**: Every piece of information (headers, interactive elements, hexadecimal dumps, borders) exists strictly on a monospace character grid. Nothing exists "between" lines or characters.
*   **Absence of GUI Elements**: There are no boxes, cards, shadows, rounded corners, or conventional buttons. Interactive elements are simply text strings on the grid that react to input (e.g., by inverting phosphor colors).

## 3. Typography and Rendering
*   **Font**: A mechanical, purely monospaced font with square-ish proportions is essential. It must look like terminal output, not a modern developer console.
*   **Color Hierarchy**: The screen is not a uniform neon green. It relies on a hierarchy of phosphor brightness:
    *   **Dim/Dark Green**: Background structures, less important text, inactive states.
    *   **Medium Green**: Standard text output.
    *   **Bright Green**: Highlights, active cursors, important alerts.
    *   **Inverse (Black on Green)**: The primary method for showing selection or focus.
*   **CRT Characteristics**: The rendering must feel physical. This means subtle scanlines, a soft bloom/glow (not a heavy Gaussian blur), slight vignette at the edges, and minor imperfections. It should *not* look like a heavy Instagram filter; the text must remain highly legible.

## 4. Specific Screen Behaviors
*   **Main Menu / Boot**: The boot sequence and menus are continuous streams of text. Options like `>> LOGIN` are just part of the text buffer. A blinking cursor `>` sits at the bottom.
*   **Hacking Screen (`wordchoice.png`)**: Candidate passwords are not UI buttons. They are strings embedded seamlessly into a stream of random junk characters and hex addresses. Only the specific hovered characters change state (via inverse highlight), not a surrounding bounding box.
*   **Input Handling**: Standard `QLineEdit` widgets must not be visible. Text input must appear as characters typed directly onto the terminal grid at the cursor's location.

## Conclusion
The application must transition from a "Qt application with green text" to a **"Terminal Emulator"**. The underlying architecture must be a central `TerminalGrid` (a 2D array of characters and their color attributes) that is painted entirely in a single pass by a custom renderer. All screens (Boot, Menu, Hacking) will manipulate this 2D character buffer rather than managing individual Qt widgets.
