# BioLang Documentation (v0.1 Draft)

# Introduction

BioLang is a biology-inspired programming language that replaces traditional programming terminology with biological concepts. Its goal is to make programming easier to understand for biology students while remaining a practical language.

File extension:

```text
.bio
```

---

# Program Structure

Every program begins with a `CULTURE` block.

```bio
CULTURE Hello
{
    EXCRETION("Hello BioLang").
}
```

Statements end with a period (`.`).

Blocks use `{}`.

---

# Comments

BioLang supports **single-line comments only**.

```bio
Note: This prints a greeting

EXCRETION("Hello").
```

Multiline comments are not supported.

---

# Variables

Variables are declared using `INOCULUM`.

```bio
INOCULUM age = 18.
INOCULUM name = "Mohsin".
INOCULUM bmi = 23.7.
```

Variable names:
- Start with a letter or `_`
- May contain numbers
- Cannot use reserved keywords

---

# Input & Output

Input:

```bio
INOCULUM name = RESPIRATE().
```

Prompted input:

```bio
INOCULUM age = RESPIRATE("Enter age: ").
```

Output:

```bio
EXCRETION("Hello").
EXCRETION(name).
EXCRETION("Age:", age).
```

---

# Arithmetic Operators

| Operator | Meaning |
|-----------|---------|
| SUM | Addition |
| FUSE | Subtraction |
| PRODUCT | Multiplication |
| CLEAVE | Division |

Example:

```bio
INOCULUM total = a SUM b.
```

---

# Comparison Operators

| Keyword | Meaning |
|----------|---------|
| GRADIENT | > |
| DEFICIT | < |
| EQUALS | == |

---

# Conditions

```bio
PATHWAY_CASCADE
{
    TRIGGER(age DEFICIT 18)
    {
        EXCRETION("Minor").
    }

    STIMULUS(age EQUALS 18)
    {
        EXCRETION("Exactly 18").
    }

    HOMEOSTASIS
    {
        EXCRETION("Adult").
    }
}
```

---

# Arrays

```bio
INOCULUM_CHAIN dna =
{
    "A",
    "T",
    "G",
    "C"
}.
```

---

# Functions

```bio
CATALYST greet(INOCULUM name)
{
    EXCRETION("Hello", name).
}

SYNTHESIZE greet("Mohsin").
```

Use `RETURN` to return values.

---

# Reserved Keywords

- CULTURE
- INOCULUM
- INOCULUM_CHAIN
- RESPIRATE
- EXCRETION
- PATHWAY_CASCADE
- TRIGGER
- STIMULUS
- HOMEOSTASIS
- CATALYST
- SYNTHESIZE
- RETURN
- SUM
- PRODUCT
- CLEAVE
- FUSE
- GRADIENT
- DEFICIT
- EQUALS

---

# Coding Style

- One statement per line.
- Always end statements with `.`
- Use descriptive variable names.
- Use `Note:` for comments.

---

# Example Program

```bio
Note: Age checker

CULTURE Main
{
    INOCULUM age = RESPIRATE("Enter age: ").

    PATHWAY_CASCADE
    {
        TRIGGER(age DEFICIT 18)
        {
            EXCRETION("Developing specimen.").
        }

        HOMEOSTASIS
        {
            EXCRETION("Mature specimen.").
        }
    }
}
```

---

# Roadmap

Version 0.1
- Variables
- Input/Output
- Arithmetic
- Conditions
- Arrays
- Functions

Future:
- Loops
- Classes
- Modules
- Package manager
- VS Code extension
- Native compiler
