// script.js – Calculator core functionality
// This script assumes it is loaded after the DOM (via <script src="script.js"></script>)
// but also safely initializes on DOMContentLoaded.

(() => {
  // ---------- Element References ----------
  const display = document.getElementById('display');
  const buttons = document.querySelectorAll('#calculator button');

  // ---------- State Management ----------
  let currentInput = '';
  let previousValue = null; // number stored before an operator
  let operator = null; // '+', '-', '*', '/'
  let shouldResetDisplay = false; // flag to clear display on next number entry

  // ---------- Utility Functions ----------
  function updateDisplay(value) {
    display.value = value;
  }

  function appendNumber(num) {
    // Reset display if we just performed an operation
    if (shouldResetDisplay) {
      currentInput = '';
      shouldResetDisplay = false;
    }
    // Prevent multiple leading zeros (except for "0.")
    if (num === '0' && currentInput === '0') return;
    // Prevent multiple decimals
    if (num === '.' && currentInput.includes('.')) return;
    // If starting fresh, avoid leading zeros before a decimal
    if (currentInput === '' && num === '.') {
      currentInput = '0.';
    } else {
      currentInput += num;
    }
    updateDisplay(currentInput);
  }

  function chooseOperator(op) {
    // If there is already a pending operation, compute it first
    if (operator && !shouldResetDisplay) {
      const result = compute();
      if (result === 'Error') {
        clearAll();
        updateDisplay('Error');
        return;
      }
      previousValue = parseFloat(result);
    } else if (currentInput !== '') {
      previousValue = parseFloat(currentInput);
    }
    operator = op;
    shouldResetDisplay = true; // next number entry should start fresh
  }

  function compute() {
    if (operator === null || previousValue === null) return currentInput || '0';
    const current = parseFloat(currentInput);
    let result;
    switch (operator) {
      case '+':
        result = previousValue + current;
        break;
      case '-':
        result = previousValue - current;
        break;
      case '*':
        result = previousValue * current;
        break;
      case '/':
        if (current === 0) return 'Error';
        result = previousValue / current;
        break;
      default:
        return '0';
    }
    // Round to avoid floating point artefacts (optional)
    result = Math.round(result * 1e12) / 1e12;
    // Prepare state for further chaining
    currentInput = result.toString();
    updateDisplay(currentInput);
    // Reset operator but keep previousValue for repeated equals if desired
    operator = null;
    previousValue = null;
    shouldResetDisplay = true;
    return currentInput;
  }

  function clearAll() {
    currentInput = '';
    previousValue = null;
    operator = null;
    shouldResetDisplay = false;
    updateDisplay('0');
  }

  function backspace() {
    if (shouldResetDisplay) {
      // If we are in a reset state, backspace should act on the result displayed
      currentInput = '';
      shouldResetDisplay = false;
    }
    currentInput = currentInput.slice(0, -1);
    if (currentInput === '' || currentInput === '-') {
      currentInput = '0';
    }
    updateDisplay(currentInput);
  }

  // ---------- Event Handlers ----------
  function handleButtonClick(e) {
    const action = e.target.dataset.action;
    const value = e.target.dataset.value;
    switch (action) {
      case 'digit':
        appendNumber(value);
        break;
      case 'decimal':
        appendNumber('.');
        break;
      case 'add':
        chooseOperator('+');
        break;
      case 'subtract':
        chooseOperator('-');
        break;
      case 'multiply':
        chooseOperator('*');
        break;
      case 'divide':
        chooseOperator('/');
        break;
      case 'equals':
        compute();
        break;
      case 'clear':
        clearAll();
        break;
      case 'backspace':
        backspace();
        break;
      default:
        // No action needed
        break;
    }
  }

  // Attach click listeners to all calculator buttons
  buttons.forEach(btn => btn.addEventListener('click', handleButtonClick));

  // ---------- Keyboard Support ----------
  function handleKeydown(e) {
    const key = e.key;
    if (/[0-9]/.test(key)) {
      appendNumber(key);
    } else if (key === '.' || key === ',') {
      appendNumber('.');
    } else if (key === '+' || key === '-') {
      chooseOperator(key);
    } else if (key === '*' || key === 'x' || key === 'X') {
      chooseOperator('*');
    } else if (key === '/' || key === '÷') {
      chooseOperator('/');
    } else if (key === 'Enter' || key === '=') {
      e.preventDefault();
      compute();
    } else if (key === 'Backspace') {
      backspace();
    } else if (key === 'Escape') {
      clearAll();
    }
  }

  document.addEventListener('keydown', handleKeydown);

  // Initialize display
  updateDisplay('0');
})();
