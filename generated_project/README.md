# SimpleCalculator

## Description
SimpleCalculator is a lightweight, web‑based calculator built with **HTML**, **CSS**, and **vanilla JavaScript**. It provides a clean UI for basic arithmetic (addition, subtraction, multiplication, division) and includes keyboard support, clear and backspace utilities, and basic error handling (e.g., division by zero).

---

## Tech Stack
- **HTML5** – Structure of the calculator UI.
- **CSS3** – Styling and layout (see `styles.css`).
- **JavaScript (ES6)** – Core logic, state management, and event handling (see `script.js`).

---

## Setup Instructions
1. **Clone the repository**
   ```bash
   git clone https://github.com/your‑username/simple‑calculator.git
   cd simple‑calculator
   ```
2. **Open the application**
   - Locate `index.html` in the project root.
   - Open it in any modern web browser (Chrome, Firefox, Edge, Safari, etc.) by double‑clicking the file or using `File → Open`.
   - No build steps, package managers, or servers are required.

---

## Usage Guide
### Button Layout
| Row | Buttons |
|-----|---------|
| 1 | **7**, **8**, **9**, **÷** |
| 2 | **4**, **5**, **6**, **×** |
| 3 | **1**, **2**, **3**, **−** |
| 4 | **0**, **.**, **=**, **+** |
| 5 | **C** (clear), **←** (backspace) |

- **Digits (0‑9)** – Append the number to the current entry.
- **Decimal (.)** – Adds a decimal point; multiple decimals are prevented.
- **Operators (+, −, ×, ÷)** – Store the current value and await the next operand.
- **Equals (=)** – Executes the pending operation and shows the result.
- **Clear (C)** – Resets the calculator to its initial state.
- **Backspace (←)** – Deletes the last character of the current entry.

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| 0‑9 | Enter digit |
| . or , | Decimal point |
| +, - | Add / Subtract |
| *, x, X | Multiply |
| /, ÷ | Divide |
| Enter or = | Compute result |
| Backspace | Delete last digit |
| Escape | Clear all |

### Error Messages
- **Division by zero** – The display shows `Error` and the calculator resets automatically.
- **Invalid input** – The UI prevents malformed numbers (e.g., multiple decimal points, leading zeros without a decimal).

---

## Development Notes
### File Responsibilities
- **`index.html`** – Defines the DOM structure: input display, buttons, and script inclusion.
- **`styles.css`** – Handles visual layout, responsive sizing, and button aesthetics.
- **`script.js`** – Implements a small state machine to manage calculator logic.

### JavaScript State Machine Overview
The calculator maintains four core pieces of state:
1. `currentInput` – String representation of the number currently being typed.
2. `previousValue` – Numeric value stored when an operator is selected.
3. `operator` – The pending arithmetic operator (`+`, `-`, `*`, `/`).
4. `shouldResetDisplay` – Boolean flag indicating that the next digit entry should start a fresh number (used after an operation or when an operator is chosen).

Key functions:
- `appendNumber(num)` – Handles digit and decimal entry, respecting the reset flag.
- `chooseOperator(op)` – Saves the current input as `previousValue`, sets the operator, and prepares for the next number.
- `compute()` – Performs the arithmetic using `previousValue`, `currentInput`, and `operator`. Handles division‑by‑zero errors.
- `clearAll()` – Resets all state variables and the display.
- `backspace()` – Removes the last character of `currentInput`.

Event handling:
- **Button clicks** – Delegated via `handleButtonClick`, which reads `data-action` and `data-value` attributes.
- **Keyboard** – Global `keydown` listener maps keys to the same functions used by the UI.

### Extending the Calculator
To add more operations (e.g., exponentiation, modulus, or scientific functions):
1. Add a new button in `index.html` with appropriate `data-action` and `data-value` attributes.
2. Extend the `switch` statement in `handleButtonClick` (or create a dedicated handler) to call a new function.
3. Update the `compute()` function to recognize the new operator symbol and perform the calculation.
4. Optionally, adjust the UI/keyboard mapping in `handleKeydown` for convenient shortcuts.

---

## License
MIT License (placeholder). See the `LICENSE` file for details.
