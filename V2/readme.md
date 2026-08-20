# BioLang 🧬

**BioLang** is an experimental, biology-inspired custom programming language implemented in **Python**.

Instead of traditional programming terminology, BioLang uses concepts inspired by biology, cells, organisms, and biological processes. The goal is to make programming feel like building and controlling a living ecosystem.

> **BioLang — Where Biology Meets Programming.**

---

## 🧬 Overview

BioLang provides familiar programming concepts through biological terminology.

For example:

| Traditional Programming | BioLang |
|---|---|
| Variable | `INOCULUM` |
| Array | `INOCULUM_CHAIN` |
| Print / Output | `EXCRETION` |
| Input | `RESPIRATE` |
| If | `TRIGGER` |
| Else If | `STIMULUS` |
| Else | `HOMEOSTASIS` |
| Loop | `CATALYST` |
| Function | `SYNTHESIZE` |
| Return | `RETURN` |
| Break | `BREAK` |
| Continue | `CONTINUE` |

The language is designed to keep programming concepts recognizable while giving them a biological identity.

---

## ✨ Features

### 🧫 Biological Terminology

BioLang replaces conventional programming keywords with biology-inspired terminology.

```biolang
INOCULUM cell_count = 100.

EXCRETION(cell_count).
```

---

### 🧬 Variables

Variables are declared using `INOCULUM`.

```biolang
INOCULUM cell_count = 100.
INOCULUM organism = "Bacteria".
INOCULUM temperature = 37.
```

Variables can be used in expressions:

```biolang
INOCULUM cells = 50.
INOCULUM new_cells = cells + 25.

EXCRETION(new_cells).
```

---

### 🧪 Arrays

BioLang supports arrays through `INOCULUM_CHAIN`.

```biolang
INOCULUM_CHAIN scores = [10, 20, 30].
```

Arrays use **zero-based indexing**:

```biolang
EXCRETION(scores[0]).
EXCRETION(scores[1]).
EXCRETION(scores[2]).
```

BioLang also performs runtime bounds checking when accessing array elements.

---

### 🗣️ Output

`EXCRETION` is used to display output.

```biolang
EXCRETION("Culture growing successfully.").
```

Variables and expressions can also be printed:

```biolang
INOCULUM cells = 100.

EXCRETION(cells).
```

---

### 🌬️ Input

`RESPIRATE` is used to receive input.

```biolang
RESPIRATE(user_input).
```

This allows BioLang programs to interact with the user.

---

## 🔀 Control Flow

BioLang provides biological terminology for conditional execution.

### TRIGGER

`TRIGGER` works like an `if` statement.

```biolang
TRIGGER (cell_count > 50) {
    EXCRETION("Colony is thriving.").
}
```

---

### STIMULUS

`STIMULUS` works like an `else if` statement.

```biolang
TRIGGER (cell_count > 50) {
    EXCRETION("Colony is thriving.").
} STIMULUS (cell_count > 20) {
    EXCRETION("Colony is stable.").
}
```

---

### HOMEOSTASIS

`HOMEOSTASIS` works like an `else` statement.

```biolang
TRIGGER (cell_count > 50) {
    EXCRETION("Colony is thriving.").
} STIMULUS (cell_count > 20) {
    EXCRETION("Colony is stable.").
} HOMEOSTASIS {
    EXCRETION("Colony is depleting.").
}
```

Together, these constructs provide conditional branching while maintaining BioLang's biological theme.

---

## 🔄 Loops

### CATALYST

`CATALYST` is BioLang's looping construct.

```biolang
INOCULUM cell_count = 5.

CATALYST (cell_count > 0) {
    EXCRETION(cell_count).
    INOCULUM cell_count = cell_count - 1.
}
```

The loop continues while its condition evaluates to true.

---

### BREAK

`BREAK` stops the current loop.

```biolang
CATALYST (cell_count > 0) {
    TRIGGER (cell_count == 2) {
        BREAK.
    }

    INOCULUM cell_count = cell_count - 1.
}
```

---

### CONTINUE

`CONTINUE` skips the remaining statements in the current iteration and proceeds to the next iteration.

```biolang
CATALYST (cell_count > 0) {
    INOCULUM cell_count = cell_count - 1.

    TRIGGER (cell_count == 2) {
        CONTINUE.
    }

    EXCRETION(cell_count).
}
```

---

## 🧬 Functions

BioLang uses `SYNTHESIZE` to declare functions.

```biolang
SYNTHESIZE replicate_cell(factor) {
    INOCULUM result = factor * 2.
    RETURN result.
}
```

A function can accept parameters and return a value.

Conceptually:

```text
SYNTHESIZE
    ↓
Create a biological process
    ↓
Receive parameters
    ↓
Perform operations
    ↓
RETURN a result
```

---

## 📖 Syntax Quick Reference

### Variables

```biolang
INOCULUM variable = value.
```

### Arrays

```biolang
INOCULUM_CHAIN array = [value1, value2, value3].
```

### Array Indexing

```biolang
EXCRETION(array[0]).
```

### Output

```biolang
EXCRETION(value).
```

### Input

```biolang
RESPIRATE(variable).
```

### Conditional

```biolang
TRIGGER (condition) {
    statements
}
```

### Else If

```biolang
STIMULUS (condition) {
    statements
}
```

### Else

```biolang
HOMEOSTASIS {
    statements
}
```

### Loop

```biolang
CATALYST (condition) {
    statements
}
```

### Function

```biolang
SYNTHESIZE function_name(parameter) {
    statements
    RETURN value.
}
```

### Break

```biolang
BREAK.
```

### Continue

```biolang
CONTINUE.
```

---

## 🧪 Complete Example

```biolang
CULTURE {

    INOCULUM cell_count = 100.

    EXCRETION("Starting biological simulation.").

    TRIGGER (cell_count > 50) {
        EXCRETION("Colony is thriving.").
    } STIMULUS (cell_count > 20) {
        EXCRETION("Colony is stable.").
    } HOMEOSTASIS {
        EXCRETION("Colony is depleting.").
    }

    CATALYST (cell_count > 0) {
        EXCRETION(cell_count).
        INOCULUM cell_count = cell_count - 1.
    }
}
```

---

# 🏗️ Project Architecture

BioLang is implemented in Python and is divided into several core components.

```text
BioLang/
│
├── main.py
├── lexar.py
├── parser.py
│
├── examples/
│   ├── hello.bio
│   ├── calculator.bio
│   ├── condition.bio
│   └── function.bio
│
└── README.md
```

### `main.py`

The main entry point of the BioLang interpreter.

It is responsible for launching the execution environment and processing BioLang programs.

---

### `lexar.py`

The lexer/tokenizer breaks BioLang source code into structured tokens.

It recognizes:

- Keywords
- Identifiers
- Numbers
- Strings
- Operators
- Parentheses
- Braces
- Brackets
- Other syntax symbols

For example:

```biolang
INOCULUM_CHAIN scores = [10, 20, 30].
```

is converted into tokens that the parser can understand.

---

### `parser.py`

The parser analyzes the token stream and determines how the BioLang program should be interpreted.

It handles language constructs such as:

- Variable declarations
- Array declarations
- Array indexing
- Expressions
- Conditions
- Loops
- Functions
- Return statements
- Break and continue
- Runtime execution
- Variable memory management
- Error handling

---

# ⚙️ How BioLang Works

BioLang follows a basic interpreter pipeline:

```text
        BioLang Source Code
                │
                ▼
          ┌───────────┐
          │   Lexer   │
          └───────────┘
                │
                ▼
             Tokens
                │
                ▼
          ┌───────────┐
          │   Parser  │
          └───────────┘
                │
                ▼
       Parsed Statements
                │
                ▼
          ┌───────────┐
          │ Execution │
          └───────────┘
                │
                ▼
             Output
```

### 1. Source Code

The programmer writes a `.bio` program.

### 2. Lexing

The lexer reads the source code and converts it into tokens.

### 3. Parsing

The parser analyzes those tokens and identifies the structure of the program.

### 4. Execution

The interpreter executes the parsed statements and produces the program's output.

---

# 📁 BioLang File Extension

BioLang source files use the:

```text
.bio
```

extension.

Example:

```text
hello.bio
calculator.bio
condition.bio
function.bio
```

---

# 🚀 Getting Started

## Requirements

Before running BioLang, make sure Python is installed.

Check your Python installation:

```bash
python --version
```

or:

```bash
python3 --version
```

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
```

Enter the project directory:

```bash
cd BioLang
```

No external programming language runtime is required because BioLang is implemented using Python.

---

## ▶️ Running BioLang

Run the main interpreter:

```bash
python main.py
```

You can also execute a BioLang source file depending on the interpreter configuration:

```bash
python main.py examples/hello.bio
```

---

# 🧫 Example Programs

BioLang includes example programs demonstrating different language features.

| Example | Purpose |
|---|---|
| `hello.bio` | Basic output |
| `calculator.bio` | Variables and expressions |
| `condition.bio` | Conditional branching |
| `function.bio` | Functions and return values |

These examples can be used to understand the language syntax and test the interpreter.

---

# ⚠️ Project Status

BioLang is an **experimental programming language project**.

The language and interpreter are actively developed and may change as new features and improvements are introduced.

The current implementation focuses on core programming concepts including:

- Variables
- Arrays
- Input/output
- Expressions
- Conditional statements
- Loops
- Functions
- Return statements
- Loop control
- Runtime validation
- Error handling

---

# 🎯 Project Goals

BioLang aims to:

- Create a programming language with a unique biological identity.
- Make programming terminology more approachable for biology-oriented learners.
- Demonstrate how programming languages are designed and implemented.
- Provide a practical interpreter-building project using Python.
- Experiment with alternative programming syntax and terminology.
- Combine concepts from biology and computer science.

---

# 🧬 Why BioLang?

Traditional programming languages use concepts such as:

```text
variables
functions
loops
conditions
arrays
return values
```

BioLang reimagines these concepts through a biological ecosystem:

```text
INOCULUM
INOCULUM_CHAIN
SYNTHESIZE
CATALYST
TRIGGER
STIMULUS
HOMEOSTASIS
EXCRETION
RESPIRATE
```

The result is a programming language where a program can be thought of as a biological process.

---

# 👨‍💻 Author

**BioLang** is an experimental programming language project created to explore the intersection of:

- 🧬 Biology
- 💻 Programming Languages
- 🐍 Python
- 🧠 Computer Science
- 🔬 Computational Thinking

---

## ⭐ BioLang

> **Code the ecosystem. Build the organism. Create BioLang.** 🧬

If you find the project interesting, consider giving it a ⭐ and exploring the source code.
