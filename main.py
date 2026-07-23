from flask import Flask, render_template_string, request, jsonify
import json
import os
import sys
import io
import re

app = Flask(__name__)

# ---------- App settings (override via environment variables) ----------
APP_SETTINGS = {
    'debug': os.environ.get('BIOLANG_DEBUG', 'true').lower() in ('1', 'true', 'yes', 'on'),
    'host': os.environ.get('BIOLANG_HOST', '0.0.0.0'),
    'port': int(os.environ.get('BIOLANG_PORT', '5000')),
    'use_reloader': os.environ.get('BIOLANG_RELOADER', 'true').lower() in ('1', 'true', 'yes', 'on'),
    'app_name': 'BioLang Cloud IDE',
    'version': '2.3',
}

# ---------- BioLang vocabulary (as defined by sir) ----------
# UNCHANGED — do not touch these rules or their order.

BIOLANG_TOKEN_RULES = (
    (r'\bINOCULUM\s+', ''),                    # variable declaration
    (r'\bRESPIRATE\s*\(', 'input('),           # input
    (r'\bEXCRETION\s*\(', 'print('),          # output
    (r'\bSUM\s+', '+ '),                       # addition
    (r'\bPRODUCT\s+', '* '),                   # multiplication
    (r'\bCLEAVE\s+', '/ '),                    # division
    (r'\bFUSE\s+', '- '),                      # subtraction
    (r'\bGRADIENT\s+', '> '),                  # greater than
    (r'\bDEFICIT\s+', '< '),                   # less than
    (r'\bEQUALS\s+', '== '),                   # equality
    (r'\bPATHWAY_CASCADE\s*\{', ''),           # if/elif/else block wrapper
    (r'\bCULTURE\s+\w+\s*\{', ''),             # culture wrapper
    (r'\bSTIMULUS\s*', 'elif '),               # elif branch (before TRIGGER)
    (r'\bTRIGGER\s*', 'if '),                  # if branch
    (r'\bHOMEOSTASIS\s*\{?', 'else:'),         # else branch
)

# Statements now terminate with a period (full stop) instead of a
# semicolon — that's how the students are taught to write it, and it's
# a REQUIRED terminator now (see _validate_statement_terminators below).
BIOLANG_CLEANUP_RULES = (
    (r'\)\s*\{', '):'),                         # brace → colon after conditions
    (r'\n\s*\}', ''),                          # closing braces
    (r'\.\s*$', ''),                            # trailing periods (was: semicolons)
    (r'^\s*\{\s*$', ''),                        # lone opening braces
    (r'^\s*\}\s*$', ''),                        # lone closing braces
)

# NOTE: 'input' is deliberately NOT in here anymore — see _make_safe_input().
# The raw builtin input() blocks on the *server's* real stdin, which has
# nothing to do with the browser user, and would hang the request forever.
SAFE_BUILTINS = {
    'print': print,
    'int': int,
    'float': float,
    'str': str,
    'bool': bool,
    'len': len,
    'range': range,
    'list': list,
    'dict': dict,
    'tuple': tuple,
    'abs': abs,
    'max': max,
    'min': min,
    'sum': sum,
    'round': round,
    'type': type,
    'True': True,
    'False': False,
    'None': None,
}

# Lines that never need a trailing period: comments, block openers
# ending in '{', and lone brace lines.
_BLOCK_OPENER_ENDINGS = ('{',)


def _validate_statement_terminators(biolang_code: str) -> str | None:
    """
    Every BioLang statement line must end with a period (full stop) —
    that's how students are taught to close a line, in place of a
    semicolon. This is now REQUIRED: a statement line missing its
    trailing period is rejected before translation even begins.

    Skipped (no period required):
      - blank lines
      - comment lines (start with '#')
      - lines that open a block, i.e. end with '{'
        (e.g. 'PATHWAY_CASCADE {', 'TRIGGER (x GRADIENT 1) {')
      - lone '{' or '}' lines

    Returns an error message string if a line is missing its period,
    otherwise None.
    """
    for i, raw_line in enumerate(biolang_code.split('\n'), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        if line in ('{', '}'):
            continue
        if line.endswith(_BLOCK_OPENER_ENDINGS):
            continue
        if not line.endswith('.'):
            return (
                f'Metabolic Failure / Syntax Error (line {i}): '
                f'statement must end with a period (full stop) — "{line}"'
            )
    return None


def _apply_rules(source: str, rules: tuple[tuple[str, str], ...]) -> str:
    for pattern, replacement in rules:
        source = re.sub(pattern, replacement, source, flags=re.MULTILINE)
    return source


def _normalize_python_source(source: str) -> str:
    lines = [line.rstrip() for line in source.split('\n')]
    return '\n'.join(lines).strip()


def _fix_orphaned_indent(source: str) -> str:
    """
    PATHWAY_CASCADE wrappers leave if/elif/else bodies indented at module level.
    Dedent one level when top-level and nested lines are mixed.
    """
    lines = source.split('\n')
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return source

    indents = [len(line) - len(line.lstrip()) for line in non_empty]
    if min(indents) != 0:
        return source

    has_nested = any(indent >= 4 for indent in indents)
    if not has_nested:
        return source

    fixed = []
    for line in lines:
        if line.strip() and line.startswith('    '):
            fixed.append(line[4:])
        else:
            fixed.append(line)
    return '\n'.join(fixed)


def translate_biolang_to_python(biolang_code: str) -> str:
    """Translates BioLang wetware syntax into executable Python code."""
    if not biolang_code or not biolang_code.strip():
        return ''

    error = _validate_statement_terminators(biolang_code)
    if error:
        raise SyntaxError(error)

    py_code = _apply_rules(biolang_code, BIOLANG_TOKEN_RULES)
    py_code = _apply_rules(py_code, BIOLANG_CLEANUP_RULES)
    py_code = _fix_orphaned_indent(py_code)
    return _normalize_python_source(py_code)


def _make_safe_input(stdin_lines: list[str]):
    """
    Returns an input()-compatible callable that consumes pre-supplied lines
    instead of blocking on the server's real stdin. Raises a friendly
    EOFError (caught upstream and shown as a Metabolic Failure) once the
    supplied lines run out, instead of hanging the request.
    """
    iterator = iter(stdin_lines)

    def _input(prompt=''):
        if prompt:
            sys.stdout.write(str(prompt))
        try:
            return next(iterator)
        except StopIteration:
            raise EOFError(
                'RESPIRATE ran out of nutrients — add a line to the '
                'Nutrient Feed panel for each RESPIRATE() call.'
            )
    return _input


def execute_translated_python(python_code: str, stdin_data: str = '') -> tuple[str, str | None]:
    """
    Compile and run translated Python in a restricted namespace.
    Returns (captured_stdout, error_message_or_none).
    """
    if not python_code.strip():
        return '', 'Metabolic Failure / Error: Culture plate is empty — streak some BioLang first.'

    stdout_buffer = io.StringIO()
    stdin_lines = stdin_data.splitlines()
    namespace = {
        '__builtins__': {**SAFE_BUILTINS, 'input': _make_safe_input(stdin_lines)}
    }

    try:
        compiled = compile(python_code, '<BioLang>', 'exec')
    except SyntaxError as exc:
        line_hint = f' (line {exc.lineno})' if exc.lineno else ''
        return '', f'Metabolic Failure / Syntax Error{line_hint}: {exc.msg}'

    old_stdout = sys.stdout
    sys.stdout = stdout_buffer
    try:
        exec(compiled, namespace)
    except EOFError as exc:
        return stdout_buffer.getvalue(), f'Metabolic Failure / Error: {exc}'
    except Exception as exc:
        return stdout_buffer.getvalue(), f'Metabolic Failure / Error: {exc}'
    finally:
        sys.stdout = old_stdout

    return stdout_buffer.getvalue(), None


# ---------- Sample Programs ----------
# Statements now end with a period (.) instead of a semicolon (;).

SAMPLE_PROGRAMS = {
    "Age Check": """# BioLang: Check specimen maturity
INOCULUM age = 16.
INOCULUM future_age = age SUM 10.

PATHWAY_CASCADE {
    TRIGGER (age DEFICIT 18) {
        EXCRETION("Specimen is still developing.").
    }
    HOMEOSTASIS {
        EXCRETION("Specimen is fully matured.").
    }
}

EXCRETION(future_age).""",

    "Simple Calculator": """# BioLang: Simple calculator
INOCULUM x = 42.
INOCULUM y = 8.

EXCRETION("Values: x =", x, "y =", y).
EXCRETION("Sum: ", x SUM y).
EXCRETION("Product: ", x PRODUCT y).
EXCRETION("Difference: ", x FUSE y).
EXCRETION("Quotient: ", x CLEAVE y).""",

    "User Input": """# BioLang: User input example
EXCRETION("What is your name?").
INOCULUM name = RESPIRATE().

EXCRETION("Hello,", name, "!").

INOCULUM age = RESPIRATE("Enter your age: ").
INOCULUM age_num = int(age).
INOCULUM birth_year = 2025 FUSE age_num.

EXCRETION("You were born in approximately", birth_year).""",

    "Number Guessing": """# BioLang: Number guessing
INOCULUM secret = 7.
INOCULUM guess = RESPIRATE("Guess the number (1-10): ").
INOCULUM guess_num = int(guess).

PATHWAY_CASCADE {
    TRIGGER (guess_num EQUALS secret) {
        EXCRETION("Correct! You WIN!").
    }
    HOMEOSTASIS {
        EXCRETION("Wrong! The secret was", secret).
    }
}""",

    "Grade Classifier": """# BioLang: Classify specimen performance
INOCULUM score = 85.

PATHWAY_CASCADE {
    TRIGGER (score GRADIENT 89) {
        EXCRETION("Grade: A — excellent growth!").
    }
    STIMULUS (score GRADIENT 79) {
        EXCRETION("Grade: B — healthy culture.").
    }
    STIMULUS (score GRADIENT 69) {
        EXCRETION("Grade: C — needs nutrients.").
    }
    HOMEOSTASIS {
        EXCRETION("Grade: D — metabolic stress detected.").
    }
}""",

    "Specimen Vitals": """# BioLang: Compute specimen vitals
INOCULUM mass_kg = 70.
INOCULUM height_m = 1.75.
INOCULUM height_sq = height_m PRODUCT height_m.
INOCULUM bmi = mass_kg CLEAVE height_sq.

EXCRETION("Mass (kg):", mass_kg).
EXCRETION("Height (m):", height_m).
EXCRETION("BMI:", round(bmi, 2)).

PATHWAY_CASCADE {
    TRIGGER (bmi DEFICIT 18.5) {
        EXCRETION("Status: Underweight specimen.").
    }
    STIMULUS (bmi GRADIENT 24.9) {
        EXCRETION("Status: Elevated mass index.").
    }
    HOMEOSTASIS {
        EXCRETION("Status: Normal homeostasis.").
    }
}""",

    "Temperature Convert": """# BioLang: Celsius to Fahrenheit
INOCULUM celsius = RESPIRATE("Enter temperature in Celsius: ").
INOCULUM celsius_num = float(celsius).
INOCULUM fahrenheit = celsius_num PRODUCT 1.8 SUM 32.

EXCRETION(celsius_num, "°C =", round(fahrenheit, 1), "°F")."""
}


# ---------- Interactive Tutorial ----------
# Starters / examples updated to use trailing periods instead of semicolons.

TUTORIAL_STEPS = [
    {
        'id': 'inoculum',
        'title': 'Inoculate a Variable',
        'icon': '🧫',
        'bio': 'In microbiology, <strong>inoculation</strong> introduces organisms into fresh medium. In BioLang, <code>INOCULUM</code> introduces a value into your culture plate (a variable). Every statement ends with a period, like a proper lab notation.',
        'example': 'INOCULUM strain = "E.coli".\nINOCULUM count = 42.',
        'task': 'Inoculate a variable named <code>species</code> with the string <code>"Yeast"</code>, then excrete it with <code>EXCRETION(species).</code> — remember the trailing period!',
        'starter': '# Inoculate your specimen\nINOCULUM species = "Yeast".\nEXCRETION(species).',
        'stdin': '',
        'expected_output': 'Yeast',
    },
    {
        'id': 'excretion',
        'title': 'Excrete Output',
        'icon': '🧪',
        'bio': 'Cells <strong>excrete</strong> waste and signaling molecules. <code>EXCRETION()</code> is how your colony expresses results to the outside world — like <code>print()</code> in Python.',
        'example': 'EXCRETION("Colony density: optimal").\nEXCRETION("Temp:", 37, "°C").',
        'task': 'Excrete exactly this message: <code>Hello from the petri dish!</code> — don\'t forget the closing period.',
        'starter': '# Express your colony output\nEXCRETION("Hello from the petri dish!").',
        'stdin': '',
        'expected_output': 'Hello from the petri dish!',
    },
    {
        'id': 'metabolism',
        'title': 'Metabolic Operators',
        'icon': '⚗️',
        'bio': '<strong>Metabolism</strong> transforms substrates. BioLang operators mirror biochemical math:<br>'
               '<code>SUM</code> (+) fusion &nbsp;·&nbsp; <code>FUSE</code> (−) cleavage &nbsp;·&nbsp; '
               '<code>PRODUCT</code> (×) amplification &nbsp;·&nbsp; <code>CLEAVE</code> (÷) division',
        'example': 'INOCULUM colonies = 5.\nINOCULUM doubled = colonies PRODUCT 2.\nEXCRETION("Colonies after fission:", doubled).',
        'task': 'Start with <code>base = 10</code>, compute <code>result = base PRODUCT 3 SUM 5</code>, then excrete <code>result</code>. Output should be <code>35</code>. Every line needs its period.',
        'starter': 'INOCULUM base = 10.\nINOCULUM result = base PRODUCT 3 SUM 5.\nEXCRETION(result).',
        'stdin': '',
        'expected_output': '35',
    },
    {
        'id': 'respirate',
        'title': 'Respirate (Input)',
        'icon': '🧬',
        'bio': '<strong>Respiration</strong> pulls nutrients from the environment. <code>RESPIRATE()</code> reads a line from the <em>Nutrient Feed</em> — one line per call, in order.',
        'example': 'INOCULUM name = RESPIRATE("Specimen ID: ").\nEXCRETION("Logged:", name).',
        'task': 'Use <code>RESPIRATE()</code> to read a specimen name, then excrete <code>Welcome, &lt;name&gt;!</code> We will feed the nutrient <code>Ada</code>.',
        'starter': 'INOCULUM name = RESPIRATE("Name: ").\nEXCRETION("Welcome,", name, "!").',
        'stdin': 'Ada',
        'expected_output': 'Welcome, Ada !',
    },
    {
        'id': 'pathway',
        'title': 'Pathway Cascade (Branching)',
        'icon': '🔬',
        'bio': 'Signaling <strong>pathways</strong> branch on conditions. <code>PATHWAY_CASCADE</code> wraps branches: '
               '<code>TRIGGER</code> (if), <code>STIMULUS</code> (elif), <code>HOMEOSTASIS</code> (else). Lines that open a block with <code>{</code> do NOT need a period — only the statements inside do.',
        'example': 'PATHWAY_CASCADE {\n    TRIGGER (temp GRADIENT 37) {\n        EXCRETION("Fever detected").\n    }\n    HOMEOSTASIS {\n        EXCRETION("Homeostasis stable").\n    }\n}',
        'task': 'If <code>score GRADIENT 50</code> excrete <code>Pass</code>, else excrete <code>Fail</code>. Use <code>score = 72</code>.',
        'starter': 'INOCULUM score = 72.\n\nPATHWAY_CASCADE {\n    TRIGGER (score GRADIENT 50) {\n        EXCRETION("Pass").\n    }\n    HOMEOSTASIS {\n        EXCRETION("Fail").\n    }\n}',
        'stdin': '',
        'expected_output': 'Pass',
    },
    {
        'id': 'graduation',
        'title': 'Graduation Assay',
        'icon': '🎓',
        'bio': 'Final assay — combine inoculation, respiration, metabolism, and pathway logic like a real lab workflow.',
        'example': '# Full specimen pipeline\nINOCULUM age = RESPIRATE("Age: ").\nINOCULUM age_num = int(age).\nPATHWAY_CASCADE {\n    TRIGGER (age_num DEFICIT 18) {\n        EXCRETION("Minor specimen").\n    }\n    HOMEOSTASIS {\n        EXCRETION("Adult specimen").\n    }\n}',
        'task': 'Read age via <code>RESPIRATE</code>, convert with <code>int()</code>. If age &lt; 18 excrete <code>Juvenile</code>, else <code>Mature</code>. Nutrient feed: <code>21</code>.',
        'starter': 'INOCULUM age = RESPIRATE("Age: ").\nINOCULUM age_num = int(age).\n\nPATHWAY_CASCADE {\n    TRIGGER (age_num DEFICIT 18) {\n        EXCRETION("Juvenile").\n    }\n    HOMEOSTASIS {\n        EXCRETION("Mature").\n    }\n}',
        'stdin': '21',
        'expected_output': 'Mature',
    },
]


def validate_tutorial_step(step_id: str, biolang_code: str, stdin_data: str) -> dict:
    """Run learner code and check it against the tutorial step requirements."""
    step = next((s for s in TUTORIAL_STEPS if s['id'] == step_id), None)
    if not step:
        return {'passed': False, 'message': 'Unknown tutorial step.', 'translated': '', 'output': ''}

    try:
        translated = translate_biolang_to_python(biolang_code)
    except SyntaxError as exc:
        return {
            'passed': False,
            'message': f'Colony rejected — {exc}',
            'translated': '',
            'output': '',
        }

    stdout, error = execute_translated_python(translated, stdin_data or step.get('stdin', ''))

    if error:
        return {
            'passed': False,
            'message': f'Colony rejected — {error}',
            'translated': translated,
            'output': stdout,
        }

    expected = step['expected_output'].strip()
    actual = stdout.strip()
    if expected in actual or actual == expected:
        return {
            'passed': True,
            'message': 'Checkpoint passed — colony healthy! Advance to the next assay.',
            'translated': translated,
            'output': stdout,
        }

    return {
        'passed': False,
        'message': f'Assay mismatch. Expected output containing "{expected}", got: "{actual or "(empty)"}"',
        'translated': translated,
        'output': stdout,
    }


# ---------- HTML Template ----------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioLang Cloud IDE</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Lab bench at night, agar glowing under it */
            --bg-dark: #0a1210;
            --bg-panel: #0f1a17;
            --bg-well: #0c1614;
            --border: #223b34;
            --border-soft: #182823;
            --rim-highlight: rgba(255,255,255,0.06);
            --accent: #5ffbc0;
            --accent-soft: rgba(95, 251, 192, 0.12);
            --accent-dim: #2b8f6c;
            --amber: #ffc773;
            --amber-soft: rgba(255, 199, 115, 0.14);
            --text-primary: #e7f5ef;
            --text-secondary: #9fc4b6;
            --text-muted: #5f7d72;
            --error: #ff8578;
            --success: #7fe8b8;
            --font-mono: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
            --font-display: 'Space Grotesk', 'Inter', -apple-system, sans-serif;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
        }

        /* Ambient colony field drifting behind everything, like plates left on a bench */
        body {
            font-family: var(--font-sans);
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            padding: 24px 20px;
            position: relative;
            overflow-x: hidden;
        }

        body::before {
            content: "";
            position: fixed;
            inset: -10%;
            background-image:
                radial-gradient(circle 60px at 8% 20%, var(--accent-soft), transparent 70%),
                radial-gradient(circle 40px at 85% 15%, var(--amber-soft), transparent 70%),
                radial-gradient(circle 90px at 70% 80%, var(--accent-soft), transparent 70%),
                radial-gradient(circle 30px at 25% 85%, var(--amber-soft), transparent 70%),
                radial-gradient(circle 50px at 45% 45%, var(--accent-soft), transparent 70%);
            filter: blur(2px);
            animation: driftColonies 50s ease-in-out infinite alternate;
            z-index: 0;
            pointer-events: none;
        }

        @keyframes driftColonies {
            to { transform: translate(2%, -1.5%) scale(1.03); }
        }

        .app-container {
            max-width: 1200px;
            width: 100%;
            position: relative;
            z-index: 1;
        }

        /* Header — the lid label on the dish rack */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 26px;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-bottom: none;
            border-radius: 20px 20px 0 0;
            flex-wrap: wrap;
            gap: 12px;
            position: relative;
            overflow: hidden;
        }

        /* Signature: a printed agar-streak sequencing trace along the header base */
        .header::after {
            content: "";
            position: absolute;
            left: 0; right: 0; bottom: 0;
            height: 2px;
            background: repeating-linear-gradient(
                90deg,
                var(--accent) 0px, var(--accent) 3px,
                transparent 3px, transparent 7px,
                var(--amber) 7px, var(--amber) 9px,
                transparent 9px, transparent 15px,
                var(--accent) 15px, var(--accent) 16px,
                transparent 16px, transparent 24px
            );
            opacity: 0.5;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        /* The logo sits in its own little dish */
        .logo-dish {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.08), transparent 60%), var(--bg-well);
            border: 2px solid var(--border);
            box-shadow: inset 0 0 0 3px rgba(0,0,0,0.25), inset 0 2px 4px var(--rim-highlight);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 19px;
            flex-shrink: 0;
        }

        .header h1 {
            font-family: var(--font-display);
            font-size: 19px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: 0.2px;
        }

        .header-subtitle {
            font-size: 11.5px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            display: block;
            margin-top: 2px;
        }

        .sample-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .sample-selector label {
            font-size: 12.5px;
            color: var(--text-secondary);
            font-family: var(--font-mono);
        }

        .sample-selector select {
            background: var(--bg-well);
            color: var(--text-primary);
            border: 1px solid var(--border);
            padding: 7px 12px;
            border-radius: 7px;
            font-family: var(--font-sans);
            font-size: 13px;
            cursor: pointer;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .sample-selector select:hover,
        .sample-selector select:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-soft);
        }

        /* Pulsing "growing" indicator instead of a static LIVE badge */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 10px;
            background: var(--bg-well);
            color: var(--accent);
            border: 1px solid var(--border);
            padding: 4px 10px 4px 8px;
            border-radius: 20px;
            font-weight: 700;
            letter-spacing: 0.6px;
            font-family: var(--font-mono);
        }

        .badge-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 0 0 rgba(95,251,192,0.6);
            animation: colonyPulse 2s ease-out infinite;
        }

        @keyframes colonyPulse {
            0%   { box-shadow: 0 0 0 0 rgba(95,251,192,0.55); }
            70%  { box-shadow: 0 0 0 7px rgba(95,251,192,0); }
            100% { box-shadow: 0 0 0 0 rgba(95,251,192,0); }
        }

        /* Main Content */
        .main-content {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-top: 1px solid var(--border-soft);
            padding: 26px;
            border-radius: 0 0 20px 20px;
        }

        .editor-section { margin-bottom: 28px; }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .section-header h3 {
            font-family: var(--font-display);
            font-size: 13.5px;
            font-weight: 600;
            color: var(--accent);
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-actions {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 15px;
            border: none;
            border-radius: 7px;
            font-family: var(--font-sans);
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
        }

        .btn-secondary {
            background: var(--bg-well);
            color: var(--text-secondary);
            border: 1px solid var(--border);
        }
        .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
        .btn-secondary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

        /* The run control is styled as a dish lid you press down to seal + incubate */
        .btn-incubate {
            background: var(--accent);
            color: #06231a;
            padding: 8px 18px 8px 14px;
            border-radius: 999px;
            box-shadow: inset 0 2px 0 rgba(255,255,255,0.35), 0 4px 14px rgba(95,251,192,0.2);
        }
        .btn-incubate:hover {
            background: #7dffce;
            transform: translateY(-1px);
            box-shadow: inset 0 2px 0 rgba(255,255,255,0.4), 0 6px 18px rgba(95,251,192,0.3);
        }
        .btn-incubate:active { transform: translateY(0); }
        .btn-incubate:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
        .btn-incubate:disabled { opacity: 0.55; cursor: not-allowed; transform: none !important; }

        /* Petri-dish framing shared by editor + output cards:
           rounded rim, faint inner highlight arc like light on glass,
           two small "stacking nubs" on the top edge like a real dish lid */
        .dish {
            position: relative;
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            background: var(--bg-well);
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .dish::before {
            content: "";
            position: absolute;
            top: 0; left: 10%; right: 10%;
            height: 10px;
            background: linear-gradient(180deg, var(--rim-highlight), transparent);
            border-radius: 0 0 50% 50% / 0 0 100% 100%;
            pointer-events: none;
        }

        .dish::after {
            content: "";
            position: absolute;
            top: -3px; left: 50%;
            width: 34px; height: 6px;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 0 0 6px 6px;
            transform: translateX(-50%);
        }

        .editor-wrapper.dish:focus-within {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-soft);
        }

        .editor-container {
            display: flex;
            min-height: 220px;
        }

        .line-numbers {
            padding: 14px 0;
            min-width: 46px;
            text-align: right;
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 13px;
            line-height: 1.6;
            user-select: none;
            border-right: 1px solid var(--border-soft);
            background: rgba(0,0,0,0.15);
        }

        /* Graduated markings like a pipette barrel — every 5th line ticked in accent */
        .line-numbers span { display: block; padding: 0 10px 0 14px; }
        .line-numbers span.tick { color: var(--accent); font-weight: 600; }

        textarea#code {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            resize: vertical;
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 13.5px;
            line-height: 1.6;
            padding: 14px 16px;
            min-height: 220px;
            width: 100%;
        }

        textarea#code::placeholder { color: var(--text-muted); opacity: 0.7; }

        .char-count {
            font-size: 11px;
            color: var(--text-muted);
            padding: 7px 14px;
            text-align: right;
            background: rgba(0,0,0,0.15);
            border-top: 1px solid var(--border-soft);
            font-family: var(--font-mono);
        }

        /* Nutrient Feed (simulated stdin) panel */
        .stdin-section { margin-top: 14px; }

        .stdin-hint {
            font-size: 11px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            margin-bottom: 8px;
        }

        textarea#stdinInput {
            width: 100%;
            background: transparent;
            border: none;
            outline: none;
            resize: vertical;
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 13px;
            line-height: 1.6;
            padding: 12px 16px;
            min-height: 70px;
        }

        textarea#stdinInput::placeholder { color: var(--text-muted); opacity: 0.7; }

        .stdin-wrapper.dish:focus-within {
            border-color: var(--amber);
            box-shadow: 0 0 0 3px var(--amber-soft);
        }

        .output-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
        }

        @media (max-width: 768px) {
            .output-section { grid-template-columns: 1fr; }
            .header { flex-direction: column; align-items: flex-start; }
            .sample-selector { width: 100%; }
            .sample-selector select { flex: 1; }
        }

        .output-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 9px 14px;
            background: rgba(0,0,0,0.2);
            border-bottom: 1px solid var(--border-soft);
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            font-family: var(--font-display);
        }

        .output-panel-body {
            padding: 14px 16px;
            font-family: var(--font-mono);
            font-size: 13px;
            line-height: 1.6;
            min-height: 120px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .output-panel-body::-webkit-scrollbar { width: 6px; }
        .output-panel-body::-webkit-scrollbar-track { background: var(--bg-well); }
        .output-panel-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        .output-panel-body::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        .output-text { color: var(--success); }
        .error-text { color: var(--error); }
        .translated-text { color: var(--text-secondary); }

        /* Empty state reads as an unincubated plate: outline only, nothing growing yet */
        .empty-state {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-muted);
            font-family: var(--font-sans);
            font-size: 12.5px;
            font-style: normal;
        }

        .empty-dish-icon {
            width: 22px;
            height: 22px;
            flex-shrink: 0;
            border-radius: 50%;
            border: 1.5px dashed var(--border);
        }

        .copy-toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--accent);
            color: #06231a;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s ease;
            pointer-events: none;
            z-index: 100;
        }

        .copy-toast.show { opacity: 1; transform: translateY(0); }

        .spinner {
            display: inline-block;
            width: 13px;
            height: 13px;
            border: 2px solid rgba(6,35,26,0.35);
            border-top-color: #06231a;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .kbd {
            display: inline-block;
            padding: 1px 5px;
            font-size: 10px;
            font-family: var(--font-mono);
            background: rgba(255,255,255,0.08);
            border: 1px solid var(--border);
            border-radius: 3px;
            color: var(--text-muted);
        }

        .header-nav {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .nav-link {
            font-size: 12.5px;
            font-weight: 600;
            color: var(--text-secondary);
            text-decoration: none;
            padding: 6px 12px;
            border-radius: 7px;
            border: 1px solid transparent;
            transition: all 0.15s ease;
        }

        .nav-link:hover { color: var(--accent); border-color: var(--border); background: var(--accent-soft); }
        .nav-link.active { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }

        .badge-debug {
            background: var(--amber-soft);
            color: var(--amber);
            border-color: rgba(255, 199, 115, 0.35);
        }

        .settings-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.65);
            z-index: 200;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .settings-overlay.open { display: flex; }

        .settings-panel {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            width: 100%;
            max-width: 480px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .settings-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 22px;
            border-bottom: 1px solid var(--border-soft);
        }

        .settings-header h2 {
            font-family: var(--font-display);
            font-size: 16px;
            color: var(--accent);
        }

        .settings-body { padding: 20px 22px 24px; }

        .settings-group { margin-bottom: 22px; }
        .settings-group:last-child { margin-bottom: 0; }

        .settings-group h3 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            margin-bottom: 12px;
        }

        .setting-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid var(--border-soft);
        }

        .setting-row:last-child { border-bottom: none; }

        .setting-label { font-size: 13px; color: var(--text-primary); }
        .setting-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

        .setting-row input[type="range"] { width: 120px; accent-color: var(--accent); }
        .setting-row select {
            background: var(--bg-well);
            color: var(--text-primary);
            border: 1px solid var(--border);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 12px;
        }

        .setting-value {
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--accent);
            min-width: 36px;
            text-align: right;
        }

        .settings-info {
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-secondary);
            background: var(--bg-well);
            border: 1px solid var(--border-soft);
            border-radius: 8px;
            padding: 12px 14px;
            line-height: 1.7;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Header -->
        <div class="header">
            <div class="header-left">
                <div class="logo-dish">🧫</div>
                <div>
                    <h1>BioLang Cloud IDE</h1>
                    <span class="header-subtitle">v{{ app_version }} &middot; wetware-to-Python transpiler</span>
                </div>
            </div>
            <div class="header-nav">
                <a href="/" class="nav-link active">IDE</a>
                <a href="/tutorial" class="nav-link">Tutorial</a>
                <button type="button" class="btn btn-secondary" onclick="openSettings()" style="padding:6px 12px;font-size:12px;">Settings</button>
            </div>
            <div class="sample-selector">
                <label for="sampleSelect">Strain</label>
                <select id="sampleSelect" onchange="loadSample(this.value)">
                    {% for name in samples.keys() %}
                    <option value="{{ name }}">{{ name }}</option>
                    {% endfor %}
                </select>
                <span class="badge"><span class="badge-dot"></span>GROWING</span>
                {% if debug_mode %}
                <span class="badge badge-debug">DEBUG</span>
                {% endif %}
            </div>
        </div>

        <!-- Main -->
        <div class="main-content">
            <!-- Editor -->
            <div class="editor-section">
                <div class="section-header">
                    <h3>🧫 Culture Plate</h3>
                    <div class="section-actions">
                        <button type="button" class="btn btn-secondary" onclick="clearEditor()" title="Wipe the plate clean">Sterilize</button>
                        <button type="button" class="btn btn-incubate" id="runBtn" onclick="submitCode()" title="Ctrl+Enter to run">
                            <span id="runIcon">▶</span>
                            <span id="runText">Incubate &amp; Run</span>
                        </button>
                    </div>
                </div>
                <div class="editor-wrapper dish">
                    <div class="editor-container">
                        <div class="line-numbers" id="lineNumbers"><span>1</span></div>
                        <textarea id="code" name="code" oninput="updateLineNumbers()" onkeydown="handleKeyDown(event)" onscroll="syncScroll()" spellcheck="false" placeholder="# Streak your BioLang colony here... (end statements with a period)">{{ default_code | e }}</textarea>
                    </div>
                    <div class="char-count">
                        Lines: <span id="lineCount">1</span> &middot; Chars: <span id="charCount">0</span>
                        <span style="float:right"><span class="kbd">Ctrl</span>+<span class="kbd">Enter</span> to run</span>
                    </div>
                </div>

                <div class="stdin-section">
                    <div class="section-header">
                        <h3>🧬 Nutrient Feed (simulated stdin)</h3>
                    </div>
                    <div class="stdin-hint">One value per line — consumed in order by each RESPIRATE() call. Leave blank if the plate doesn't RESPIRATE.</div>
                    <div class="stdin-wrapper dish">
                        <textarea id="stdinInput" name="stdin" spellcheck="false" placeholder="e.g.&#10;Ada&#10;29"></textarea>
                    </div>
                </div>
            </div>

            <!-- Outputs -->
            <div class="output-section">
                <div class="output-panel dish">
                    <div class="output-panel-header">
                        <span>🔬 Expressed Sequence</span>
                        <button type="button" class="btn btn-secondary" style="padding:4px 10px;font-size:11px;" onclick="copyTranslated()">Copy</button>
                    </div>
                    <div class="output-panel-body" id="translatedOutput">
                        {% if translated %}
                        <code class="translated-text">{{ translated | e }}</code>
                        {% else %}
                        <span class="empty-state"><span class="empty-dish-icon"></span>Nothing expressed yet — incubate a plate to see the translated Python.</span>
                        {% endif %}
                    </div>
                </div>
                <div class="output-panel dish">
                    <div class="output-panel-header">
                        <span>🧪 Assay Results</span>
                        <button type="button" class="btn btn-secondary" style="padding:4px 10px;font-size:11px;" onclick="clearOutput()">Discard</button>
                    </div>
                    <div class="output-panel-body" id="executionOutput">
                        {% if output %}
                        <code class="{% if output.startswith('Metabolic Failure') %}error-text{% else %}output-text{% endif %}">{{ output | e }}</code>
                        {% else %}
                        <span class="empty-state"><span class="empty-dish-icon"></span>No colonies yet — run your plate to see what grows.</span>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast -->
    <div class="copy-toast" id="toast">Sequence copied</div>

    <!-- Settings Modal -->
    <div class="settings-overlay" id="settingsOverlay" onclick="if(event.target===this)closeSettings()">
        <div class="settings-panel" role="dialog" aria-labelledby="settingsTitle">
            <div class="settings-header">
                <h2 id="settingsTitle">⚙️ Lab Configuration</h2>
                <button type="button" class="btn btn-secondary" onclick="closeSettings()" style="padding:4px 10px;font-size:11px;">Close</button>
            </div>
            <div class="settings-body">
                <div class="settings-group">
                    <h3>Server (read-only)</h3>
                    <div class="settings-info">
                        Debug mode: <strong>{{ 'ON' if debug_mode else 'OFF' }}</strong><br>
                        Host: <strong>{{ server_host }}</strong><br>
                        Port: <strong>{{ server_port }}</strong><br>
                        Version: <strong>{{ app_version }}</strong>
                    </div>
                </div>
                <div class="settings-group">
                    <h3>Editor Preferences</h3>
                    <div class="setting-row">
                        <div>
                            <div class="setting-label">Font size</div>
                            <div class="setting-desc">Culture plate text size</div>
                        </div>
                        <input type="range" id="setFontSize" min="11" max="20" value="13" oninput="applySettings()">
                        <span class="setting-value" id="setFontSizeVal">13px</span>
                    </div>
                    <div class="setting-row">
                        <div>
                            <div class="setting-label">Tab width</div>
                            <div class="setting-desc">Spaces inserted on Tab key</div>
                        </div>
                        <select id="setTabWidth" onchange="applySettings()">
                            <option value="2">2 spaces</option>
                            <option value="4" selected>4 spaces</option>
                        </select>
                    </div>
                    <div class="setting-row">
                        <div>
                            <div class="setting-label">Auto-run on strain load</div>
                            <div class="setting-desc">Incubate immediately when picking a sample</div>
                        </div>
                        <select id="setAutoRun" onchange="applySettings()">
                            <option value="0">Off</option>
                            <option value="1">On</option>
                        </select>
                    </div>
                </div>
                <div class="settings-group">
                    <button type="button" class="btn btn-secondary" onclick="resetSettings()" style="width:100%;justify-content:center;">Reset to defaults</button>
                </div>
            </div>
        </div>
    </div>

    <script>
    {% raw %}
        const textarea = document.getElementById('code');
        const stdinInput = document.getElementById('stdinInput');
        const lineNumbers = document.getElementById('lineNumbers');
        const lineCount = document.getElementById('lineCount');
        const charCount = document.getElementById('charCount');
        const translatedOutput = document.getElementById('translatedOutput');
        const executionOutput = document.getElementById('executionOutput');

        const EMPTY_TRANSLATED = '<span class="empty-state"><span class="empty-dish-icon"></span>Nothing expressed yet — incubate a plate to see the translated Python.</span>';
        const EMPTY_EXECUTION = '<span class="empty-state"><span class="empty-dish-icon"></span>No colonies yet — run your plate to see what grows.</span>';

        const SETTINGS_KEY = 'biolang_ide_settings';
        const defaultSettings = { fontSize: 13, tabWidth: 4, autoRun: false };

        function loadSettings() {
            try {
                const raw = localStorage.getItem(SETTINGS_KEY);
                return raw ? Object.assign({}, defaultSettings, JSON.parse(raw)) : Object.assign({}, defaultSettings);
            } catch (e) {
                return Object.assign({}, defaultSettings);
            }
        }

        function saveSettingsObj(s) {
            localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
        }

        function applySettings() {
            const s = {
                fontSize: parseInt(document.getElementById('setFontSize').value, 10),
                tabWidth: parseInt(document.getElementById('setTabWidth').value, 10),
                autoRun: document.getElementById('setAutoRun').value === '1',
            };
            saveSettingsObj(s);
            document.getElementById('setFontSizeVal').textContent = s.fontSize + 'px';
            textarea.style.fontSize = s.fontSize + 'px';
            lineNumbers.style.fontSize = s.fontSize + 'px';
        }

        function openSettings() {
            const s = loadSettings();
            document.getElementById('setFontSize').value = s.fontSize;
            document.getElementById('setTabWidth').value = String(s.tabWidth);
            document.getElementById('setAutoRun').value = s.autoRun ? '1' : '0';
            document.getElementById('setFontSizeVal').textContent = s.fontSize + 'px';
            document.getElementById('settingsOverlay').classList.add('open');
        }

        function closeSettings() {
            document.getElementById('settingsOverlay').classList.remove('open');
        }

        function resetSettings() {
            saveSettingsObj(defaultSettings);
            applySettings();
            openSettings();
        }

        function getTabSpaces() {
            const n = loadSettings().tabWidth || 4;
            return ' '.repeat(n);
        }

        function updateLineNumbers() {
            const lines = textarea.value.split('\\n');
            const count = lines.length;
            lineNumbers.innerHTML = lines.map(function(_, i) {
                const n = i + 1;
                const tickClass = (n % 5 === 0) ? ' class="tick"' : '';
                return '<span' + tickClass + '>' + n + '</span>';
            }).join('');
            lineCount.textContent = count;
            charCount.textContent = textarea.value.length;
        }

        function syncScroll() {
            lineNumbers.scrollTop = textarea.scrollTop;
        }

        function handleKeyDown(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                submitCode();
            }
            if (e.key === 'Tab') {
                e.preventDefault();
                const spaces = getTabSpaces();
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                textarea.value = textarea.value.substring(0, start) + spaces + textarea.value.substring(end);
                textarea.selectionStart = textarea.selectionEnd = start + spaces.length;
                updateLineNumbers();
            }
        }

        function setTranslatedOutput(text) {
            if (!text || !text.trim()) {
                translatedOutput.innerHTML = EMPTY_TRANSLATED;
                return;
            }
            translatedOutput.innerHTML = '<code class="translated-text"></code>';
            translatedOutput.querySelector('code').textContent = text;
        }

        function setExecutionOutput(text, isError) {
            if (!text || !text.trim()) {
                executionOutput.innerHTML = EMPTY_EXECUTION;
                return;
            }
            const cls = isError ? 'error-text' : 'output-text';
            executionOutput.innerHTML = '<code class="' + cls + '"></code>';
            executionOutput.querySelector('code').textContent = text;
        }

        function loadSample(name) {
            fetch('/load_sample', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'sample=' + encodeURIComponent(name)
            })
            .then(function(r) {
                if (!r.ok) throw new Error('Could not load sample');
                return r.text();
            })
            .then(function(code) {
                textarea.value = code;
                updateLineNumbers();
                setTranslatedOutput('');
                setExecutionOutput('');
                if (loadSettings().autoRun) submitCode();
            })
            .catch(function() {
                alert('Could not load sample. Make sure the server is running (python main.py).');
            });
        }

        function submitCode() {
            const btn = document.getElementById('runBtn');
            const icon = document.getElementById('runIcon');
            const text = document.getElementById('runText');
            btn.disabled = true;
            icon.innerHTML = '<span class="spinner"></span>';
            text.textContent = 'Incubating...';

            fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'code=' + encodeURIComponent(textarea.value) + '&stdin=' + encodeURIComponent(stdinInput.value)
            })
            .then(function(r) {
                if (!r.ok) throw new Error('Server returned ' + r.status);
                return r.json();
            })
            .then(function(data) {
                setTranslatedOutput(data.translated || '');
                setExecutionOutput(data.output || '', !!data.is_error);
            })
            .catch(function() {
                setExecutionOutput(
                    'Metabolic Failure / Error: Cannot reach server. Open a terminal in this folder and run: python main.py',
                    true
                );
            })
            .finally(function() {
                btn.disabled = false;
                icon.textContent = '\u25B6';
                text.textContent = 'Incubate & Run';
            });
        }

        function clearEditor() {
            if (confirm('Sterilize the plate? This cannot be undone.')) {
                textarea.value = '';
                updateLineNumbers();
            }
        }

        function clearOutput() {
            setTranslatedOutput('');
            setExecutionOutput('');
        }

        function copyTranslated() {
            const codeEl = translatedOutput.querySelector('code');
            const text = codeEl ? codeEl.textContent.trim() : translatedOutput.textContent.trim();
            if (!text || translatedOutput.querySelector('.empty-state')) return;

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(showCopyToast).catch(function() {
                    fallbackCopy(text);
                });
            } else {
                fallbackCopy(text);
            }
        }

        function fallbackCopy(text) {
            const tmp = document.createElement('textarea');
            tmp.value = text;
            document.body.appendChild(tmp);
            tmp.select();
            document.execCommand('copy');
            document.body.removeChild(tmp);
            showCopyToast();
        }

        function showCopyToast() {
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(function() { toast.classList.remove('show'); }, 2000);
        }

        updateLineNumbers();
        applySettings();
    {% endraw %}
    </script>
</body>
</html>
"""


TUTORIAL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioLang Tutorial — Lab Primer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a1210; --bg-panel: #0f1a17; --bg-well: #0c1614;
            --border: #223b34; --border-soft: #182823; --accent: #5ffbc0;
            --accent-soft: rgba(95,251,192,0.12); --accent-dim: #2b8f6c;
            --amber: #ffc773; --amber-soft: rgba(255,199,115,0.14);
            --text-primary: #e7f5ef; --text-secondary: #9fc4b6; --text-muted: #5f7d72;
            --error: #ff8578; --success: #7fe8b8;
            --font-mono: 'JetBrains Mono', Consolas, monospace;
            --font-display: 'Space Grotesk', sans-serif;
            --font-sans: 'Inter', system-ui, sans-serif;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:var(--font-sans); background:var(--bg-dark); color:var(--text-primary); min-height:100vh; padding:24px 20px; }
        .wrap { max-width:960px; margin:0 auto; }
        .top-bar { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:24px; }
        .top-bar h1 { font-family:var(--font-display); font-size:20px; color:var(--accent); }
        .top-bar p { font-size:12px; color:var(--text-muted); font-family:var(--font-mono); margin-top:4px; }
        .nav-link { font-size:12.5px; font-weight:600; color:var(--text-secondary); text-decoration:none; padding:6px 12px; border-radius:7px; border:1px solid var(--border); }
        .nav-link:hover { color:var(--accent); border-color:var(--accent-dim); }
        .progress-track { display:flex; gap:6px; margin-bottom:24px; flex-wrap:wrap; }
        .progress-dot { flex:1; min-width:48px; height:6px; border-radius:3px; background:var(--border); cursor:pointer; transition:background 0.2s; }
        .progress-dot.done { background:var(--accent-dim); }
        .progress-dot.active { background:var(--accent); box-shadow:0 0 8px var(--accent-soft); }
        .card { background:var(--bg-panel); border:1px solid var(--border); border-radius:16px; overflow:hidden; margin-bottom:18px; }
        .card-head { padding:16px 20px; border-bottom:1px solid var(--border-soft); display:flex; align-items:center; gap:10px; }
        .card-head h2 { font-family:var(--font-display); font-size:16px; color:var(--text-primary); }
        .step-icon { font-size:22px; }
        .card-body { padding:20px; }
        .bio-text { font-size:14px; line-height:1.65; color:var(--text-secondary); margin-bottom:16px; }
        .bio-text code { font-family:var(--font-mono); font-size:12px; background:var(--bg-well); padding:2px 6px; border-radius:4px; color:var(--accent); }
        .task-box { background:var(--amber-soft); border:1px solid rgba(255,199,115,0.25); border-radius:10px; padding:14px 16px; margin-bottom:16px; font-size:13px; line-height:1.6; }
        .task-box strong { color:var(--amber); }
        .example-label { font-size:11px; font-family:var(--font-mono); color:var(--text-muted); text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px; }
        pre.example { background:var(--bg-well); border:1px solid var(--border-soft); border-radius:8px; padding:12px 14px; font-family:var(--font-mono); font-size:12.5px; color:var(--text-secondary); overflow-x:auto; margin-bottom:18px; white-space:pre-wrap; }
        textarea.tut-code { width:100%; min-height:140px; background:var(--bg-well); border:1px solid var(--border); border-radius:10px; color:var(--text-primary); font-family:var(--font-mono); font-size:13px; line-height:1.6; padding:14px; resize:vertical; outline:none; }
        textarea.tut-code:focus { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); }
        textarea.tut-stdin { width:100%; min-height:56px; margin-top:10px; background:var(--bg-well); border:1px solid var(--border); border-radius:8px; color:var(--text-primary); font-family:var(--font-mono); font-size:12px; padding:10px 12px; resize:vertical; outline:none; }
        .stdin-label { font-size:11px; color:var(--text-muted); font-family:var(--font-mono); margin-top:14px; margin-bottom:6px; }
        .btn-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; align-items:center; }
        .btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border:none; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; transition:all 0.15s; }
        .btn-primary { background:var(--accent); color:#06231a; }
        .btn-primary:hover { background:#7dffce; }
        .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
        .btn-ghost { background:var(--bg-well); color:var(--text-secondary); border:1px solid var(--border); }
        .btn-ghost:hover { border-color:var(--accent); color:var(--accent); }
        .feedback { margin-top:16px; padding:12px 14px; border-radius:8px; font-size:13px; line-height:1.5; display:none; }
        .feedback.show { display:block; }
        .feedback.pass { background:rgba(127,232,184,0.12); border:1px solid rgba(127,232,184,0.35); color:var(--success); }
        .feedback.fail { background:rgba(255,133,120,0.1); border:1px solid rgba(255,133,120,0.3); color:var(--error); }
        .feedback.info { background:var(--accent-soft); border:1px solid var(--border); color:var(--text-secondary); }
        .output-mini { margin-top:10px; font-family:var(--font-mono); font-size:12px; color:var(--text-muted); white-space:pre-wrap; }
        .complete-banner { display:none; text-align:center; padding:32px 20px; }
        .complete-banner.show { display:block; }
        .complete-banner h2 { font-family:var(--font-display); color:var(--accent); font-size:22px; margin-bottom:8px; }
        @media(max-width:600px){ .btn-row { flex-direction:column; align-items:stretch; } }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="top-bar">
            <div>
                <h1>🧬 BioLang Lab Primer</h1>
                <p>Interactive wetware tutorial &middot; {{ step_count }} assays</p>
            </div>
            <a href="/" class="nav-link">← Back to IDE</a>
        </div>

        <div class="progress-track" id="progressTrack"></div>

        <div id="tutorialMain">
            <div class="card">
                <div class="card-head">
                    <span class="step-icon" id="stepIcon">🧫</span>
                    <h2 id="stepTitle">Loading...</h2>
                </div>
                <div class="card-body">
                    <div class="bio-text" id="stepBio"></div>
                    <div class="example-label">Reference streak</div>
                    <pre class="example" id="stepExample"></pre>
                    <div class="task-box"><strong>Your assay:</strong> <span id="stepTask"></span></div>
                    <textarea class="tut-code" id="tutCode" spellcheck="false"></textarea>
                    <div class="stdin-label" id="stdinLabel" style="display:none;">Nutrient Feed (one value per line)</div>
                    <textarea class="tut-stdin" id="tutStdin" spellcheck="false" style="display:none;"></textarea>
                    <div class="btn-row">
                        <button type="button" class="btn btn-primary" id="checkBtn" onclick="runCheckpoint()">🔬 Run Checkpoint</button>
                        <button type="button" class="btn btn-ghost" id="hintBtn" onclick="showHint()">💡 Reveal starter</button>
                        <button type="button" class="btn btn-ghost" id="prevBtn" onclick="prevStep()">← Previous</button>
                        <button type="button" class="btn btn-ghost" id="nextBtn" onclick="nextStep()" disabled>Next →</button>
                    </div>
                    <div class="feedback" id="feedback"></div>
                    <div class="output-mini" id="outputMini"></div>
                </div>
            </div>
        </div>

        <div class="card complete-banner" id="completeBanner">
            <h2>🎓 Culture Certified!</h2>
            <p style="color:var(--text-secondary);margin-bottom:16px;">You completed all BioLang assays. Your colony is ready for the full IDE.</p>
            <a href="/" class="btn btn-primary" style="text-decoration:none;display:inline-flex;">Open BioLang IDE</a>
        </div>
    </div>

    <script>
        const STEPS = {{ steps_json | safe }};
    {% raw %}
        const PROGRESS_KEY = 'biolang_tutorial_progress';
        let currentStep = 0;
        let completed = loadProgress();

        function loadProgress() {
            try {
                const raw = localStorage.getItem(PROGRESS_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (e) { return []; }
        }

        function saveProgress() {
            localStorage.setItem(PROGRESS_KEY, JSON.stringify(completed));
        }

        function renderProgress() {
            const track = document.getElementById('progressTrack');
            track.innerHTML = STEPS.map(function(s, i) {
                let cls = 'progress-dot';
                if (completed.indexOf(s.id) !== -1) cls += ' done';
                if (i === currentStep) cls += ' active';
                return '<div class="' + cls + '" title="' + s.title + '" onclick="goToStep(' + i + ')"></div>';
            }).join('');
        }

        function renderStep() {
            if (currentStep >= STEPS.length) {
                document.getElementById('tutorialMain').style.display = 'none';
                document.getElementById('completeBanner').classList.add('show');
                return;
            }
            document.getElementById('tutorialMain').style.display = 'block';
            document.getElementById('completeBanner').classList.remove('show');

            const step = STEPS[currentStep];
            document.getElementById('stepIcon').textContent = step.icon;
            document.getElementById('stepTitle').textContent = 'Assay ' + (currentStep + 1) + ': ' + step.title;
            document.getElementById('stepBio').innerHTML = step.bio;
            document.getElementById('stepExample').textContent = step.example;
            document.getElementById('stepTask').innerHTML = step.task;
            document.getElementById('tutCode').value = step.starter;
            document.getElementById('feedback').className = 'feedback';
            document.getElementById('outputMini').textContent = '';

            const hasStdin = step.stdin && step.stdin.length > 0;
            document.getElementById('stdinLabel').style.display = hasStdin ? 'block' : 'none';
            const stdinEl = document.getElementById('tutStdin');
            stdinEl.style.display = hasStdin ? 'block' : 'none';
            stdinEl.value = hasStdin ? step.stdin : '';

            document.getElementById('prevBtn').disabled = currentStep === 0;
            document.getElementById('nextBtn').disabled = completed.indexOf(step.id) === -1;
            renderProgress();
        }

        function goToStep(i) {
            if (i < 0 || i >= STEPS.length) return;
            if (i === 0 || completed.indexOf(STEPS[i - 1].id) !== -1 || completed.indexOf(STEPS[i].id) !== -1) {
                currentStep = i;
                renderStep();
            }
        }

        function showHint() {
            document.getElementById('tutCode').value = STEPS[currentStep].starter;
        }

        function runCheckpoint() {
            const btn = document.getElementById('checkBtn');
            const fb = document.getElementById('feedback');
            const step = STEPS[currentStep];
            btn.disabled = true;
            fb.className = 'feedback show info';
            fb.textContent = 'Incubating specimen...';

            const body = 'step_id=' + encodeURIComponent(step.id)
                + '&code=' + encodeURIComponent(document.getElementById('tutCode').value)
                + '&stdin=' + encodeURIComponent(document.getElementById('tutStdin').value);

            fetch('/api/tutorial/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: body
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                fb.className = 'feedback show ' + (data.passed ? 'pass' : 'fail');
                fb.textContent = data.message;
                let mini = '';
                if (data.translated) mini += 'Translated: ' + data.translated + '\\n';
                if (data.output) mini += 'Output: ' + data.output;
                document.getElementById('outputMini').textContent = mini;
                if (data.passed) {
                    if (completed.indexOf(step.id) === -1) {
                        completed.push(step.id);
                        saveProgress();
                    }
                    document.getElementById('nextBtn').disabled = false;
                }
            })
            .catch(function() {
                fb.className = 'feedback show fail';
                fb.textContent = 'Cannot reach lab server — run python main.py first.';
            })
            .finally(function() { btn.disabled = false; });
        }

        function nextStep() {
            if (completed.indexOf(STEPS[currentStep].id) === -1) return;
            currentStep++;
            renderStep();
        }

        function prevStep() {
            if (currentStep > 0) { currentStep--; renderStep(); }
        }

        renderStep();
    {% endraw %}
    </script>
</body>
</html>
"""


# ---------- Flask Routes ----------

DEFAULT_SAMPLE = next(iter(SAMPLE_PROGRAMS))


def _template_context(**extra):
    """Shared template variables for IDE pages."""
    base = {
        'debug_mode': APP_SETTINGS['debug'],
        'server_host': APP_SETTINGS['host'],
        'server_port': APP_SETTINGS['port'],
        'app_version': APP_SETTINGS['version'],
    }
    base.update(extra)
    return base


@app.route('/', methods=['GET', 'POST'])
def ide_home():
    editor_code = SAMPLE_PROGRAMS[DEFAULT_SAMPLE]
    translated_code = ''
    output = ''

    if request.method == 'POST':
        editor_code = request.form.get('code', editor_code)
        stdin_data = request.form.get('stdin', '')
        try:
            translated_code = translate_biolang_to_python(editor_code)
            output, error = execute_translated_python(translated_code, stdin_data)
            if error:
                output = error
        except SyntaxError as exc:
            translated_code = ''
            output = str(exc)

    return render_template_string(
        HTML_TEMPLATE,
        **_template_context(
            translated=translated_code,
            output=output,
            samples=SAMPLE_PROGRAMS,
            default_code=editor_code,
        ),
    )


@app.route('/tutorial')
def tutorial_page():
    return render_template_string(
        TUTORIAL_TEMPLATE,
        steps_json=json.dumps(TUTORIAL_STEPS),
        step_count=len(TUTORIAL_STEPS),
    )


@app.route('/api/tutorial/validate', methods=['POST'])
def tutorial_validate():
    step_id = request.form.get('step_id', '')
    code = request.form.get('code', '')
    stdin_data = request.form.get('stdin', '')
    return jsonify(validate_tutorial_step(step_id, code, stdin_data))


@app.route('/api/settings')
def api_settings():
    return jsonify(APP_SETTINGS)


@app.route('/api/run', methods=['POST'])
def api_run():
    code = request.form.get('code', '')
    stdin_data = request.form.get('stdin', '')
    try:
        translated = translate_biolang_to_python(code)
    except SyntaxError as exc:
        return jsonify({'translated': '', 'output': str(exc), 'is_error': True})

    stdout, error = execute_translated_python(translated, stdin_data)
    return jsonify({
        'translated': translated,
        'output': error if error else stdout,
        'is_error': error is not None,
    })


@app.route('/load_sample', methods=['POST'])
def load_sample():
    sample_name = request.form.get('sample', DEFAULT_SAMPLE)
    return SAMPLE_PROGRAMS.get(sample_name, SAMPLE_PROGRAMS[DEFAULT_SAMPLE])


@app.route('/clear', methods=['POST'])
def clear_output():
    return '', 204


if __name__ == '__main__':
    print(f" * BioLang IDE v{APP_SETTINGS['version']}")
    print(f" * Debug mode: {'ON' if APP_SETTINGS['debug'] else 'OFF'}")
    print(f" * Tutorial: http://127.0.0.1:{APP_SETTINGS['port']}/tutorial")
    print(f" * Settings: BIOLANG_DEBUG, BIOLANG_HOST, BIOLANG_PORT, BIOLANG_RELOADER")
    app.run(
        host=APP_SETTINGS['host'],
        port=APP_SETTINGS['port'],
        debug=APP_SETTINGS['debug'],
        use_reloader=APP_SETTINGS['use_reloader'],
    )