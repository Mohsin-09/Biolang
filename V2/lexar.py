from keywords import BIOLANG_KEYWORDS
symbols = "(){}[]=,."

def bioClassification(tokens):

    classified_tokens = []

    for token in tokens:

        if token == "EOF":
            classified_tokens.append(("EOF",token))

        elif token in BIOLANG_KEYWORDS:
            classified_tokens.append(("KEYWORD",token))

        elif token.isdigit() or (token.startswith('-') and token[1:].isdigit()):
            classified_tokens.append(("NUMBER",token))

        elif token.startswith('"') and token.endswith('"'):
            classified_tokens.append(("STRING",token))

        elif token in symbols:
            classified_tokens.append(("SYMBOL",token))

        else:
            classified_tokens.append(("IDENTIFIER",token))

    return classified_tokens
