from memory import VARIABLES

def evaluate_expression(left_type,left_value,operator,right_value,right_type):

    #left side
    if left_type == "IDENTIFIER":

        if left_value not in VARIABLES:
            print("Grammer Error")
            print("Unknown Variable", left_value)
            return

        left_value = VARIABLES[left_value]

    #right side
    if right_type == "IDENTIFIER":
    
        if right_value not in VARIABLES:
            print("Grammer Error")
            print("Unknown Variable", right_value)
            return
    
        right_value = VARIABLES[right_value]


    #converting to numbers
    left_value = int(left_value)
    right_value = int(right_value)

    if operator == "SUM":
        return left_value + right_value 
    

    elif operator == "PRODUCT":
            return left_value * right_value 
    
    
    elif operator == "CLEAVE":
            return left_value - right_value 
    
     
    elif operator == "FUSE":
            return left_value / right_value 
    
    else:
          print("Runtime Error")
          print("Unknown Operator")
        
    return None

def evaluate_condition(left_type, left_value, operator, right_value, right_type):

    # left var
    if left_type == "IDENTIFIER":

        if left_value not in VARIABLES:
            print("Runtime Error")
            print("Unknown Variable", left_value)
            return None

        left_value = VARIABLES[left_value]

    # right var
    if right_type == "IDENTIFIER":

        if right_value not in VARIABLES:
            print("Runtime Error")
            print("Unknown Variable", right_value)
            return None

        right_value = VARIABLES[right_value]

    # converting to numbers if they are numbers 
    try:
        left_value = int(left_value)
        right_value = int(right_value)
    except ValueError:
        # striping the "" from a string literals
        left_value = str(left_value).strip('"')
        right_value = str(right_value).strip('"')

    #checking operator
    if operator == "EQUALS":
        return left_value == right_value

    elif operator == "DEFICIT":
        return left_value < right_value

    elif operator == "GRADIENT":
        return left_value > right_value

    else:
        print("Runtime Error")
        print("Unknown Comparison Operator")
        return None