# ==========================================
# BioLang Language Keywords
# ==========================================

BIOLANG_KEYWORDS = {

    "INOCULUM": {
        "type": "KEYWORD",
        "category": "VARIABLE"
    },

    "INOCULUM_CHAIN": {
        "type": "KEYWORD",
        "category": "ARRAY"
    },

    "RESPIRATE": {
        "type": "KEYWORD",
        "category": "INPUT"
    },

    "EXCRETION": {
        "type": "KEYWORD",
        "category": "OUTPUT"
    },

    # ==========================
    # Conditions
    # ==========================
    "PATHWAY_CASCADE": {
        "type": "KEYWORD",
        "category": "CONDITIONAL"
    },

    "TRIGGER": {
        "type": "KEYWORD",
        "category": "IF"
    },

    "STIMULUS": {
        "type": "KEYWORD",
        "category": "ELSE_IF"
    },

    "HOMEOSTASIS": {
        "type": "KEYWORD",
        "category": "ELSE"
    },

    # ==========================
    # Loops
    # ==========================
    "CATALYST": {
        "type": "KEYWORD",
        "category": "LOOP"
    },

    "BREAK": {
        "type": "KEYWORD",
        "category": "LOOP_CONTROL"
    },

    "CONTINUE": {
        "type": "KEYWORD",
        "category": "LOOP_CONTROL"
    },

    # ==========================
    # Functions
    # ==========================
    "SYNTHESIZE": {
        "type": "KEYWORD",
        "category": "FUNCTION_CALL"
    },

    "RETURN": {
        "type": "KEYWORD",
        "category": "RETURN"
    },

    # ==========================
    # Arithmetic
    # ==========================
    "SUM": {
        "type": "OPERATOR",
        "category": "ARITHMETIC"
    },

    "FUSE": {
        "type": "OPERATOR",
        "category": "ARITHMETIC"
    },

    "PRODUCT": {
        "type": "OPERATOR",
        "category": "ARITHMETIC"
    },

    "CLEAVE": {
        "type": "OPERATOR",
        "category": "ARITHMETIC"
    },

    # Comparisons
    "GRADIENT": {
        "type": "OPERATOR",
        "category": "COMPARISON"
    },

    "DEFICIT": {
        "type": "OPERATOR",
        "category": "COMPARISON"
    },

    "EQUALS": {
        "type": "OPERATOR",
        "category": "COMPARISON"
    }
}