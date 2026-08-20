import sys
from lexar import bioClassification
from parser import parse_biocode
from memory import VARIABLES
from functions import FUNCTIONS

line_tokens = []
word_tokens = []
char_tokens = []
isComment = False
commentCount = 0


def read_biolang(filename): 
    with open(filename,"r") as file:
        code = file.read()
    return code

def sterilize_biocode(code):
    clean_code = []
    for line in code.splitlines():
        line = line.strip()
        if line == "":
            continue
        if line.startswith("NOTE:"):
            continue
        clean_code.append(line)

    return clean_code

def tokenizer(clean_code):
    tokens = []

    symbols = "{}(),.=[]"

    for line in clean_code:

        currentword = ""
        insideString = False

        for character in line:

            #Start of String
            if insideString:
                currentword += character

                if character == '"':
                    tokens.append(currentword)
                    currentword = ""
                    insideString = False

                continue  

            #End of String
            if character == '"':

                if currentword != "":
                    tokens.append(currentword)
                    currentword = ""

                currentword += character
                insideString = True
                continue

            #Spaces
            if character == " ":
                if currentword != "":
                    tokens.append(currentword)
                    currentword = ""
                continue

            #Symbols     
            if character in symbols:
                if currentword != "":
                    tokens.append(currentword)
                    currentword = ""
                tokens.append(character)

            #Default for no errors 
            else:
                currentword += character

        if currentword != "":
            tokens.append(currentword)

    tokens.append("EOF")    
    return tokens     
            
def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <filename.bio>")
        return

    filename = sys.argv[1]

    source_code = read_biolang(filename)
    clean_code = sterilize_biocode(source_code)
    tokens = tokenizer(clean_code)
    classified_tokens = bioClassification(tokens)
    
    print(source_code)
    print("---------------------------------------------------------------------------------------------------------------------------------------")
    print(clean_code)  
    print("---------------------------------------------------------------------------------------------------------------------------------------")  
    print(tokens)
    print("---------------------------------------------------------------------------------------------------------------------------------------")
    for token in classified_tokens:
        print(token)
    print("---------------------------------------------------------------------------------------------------------------------------------------")
    parse_biocode(classified_tokens)
    print("---------------------------------------------------------------------------------------------------------------------------------------")
    print("Memory")
    for variable in VARIABLES:
        print(variable,type(variable))
    print("---------------------------------------------------------------------------------------------------------------------------------------")
    print("Functions")
    for function in FUNCTIONS:
        print(function)
        

main()
    
          