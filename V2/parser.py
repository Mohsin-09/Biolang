from memory import VARIABLES
from runtime import evaluate_expression,evaluate_condition
from functions import FUNCTIONS

def parse_biocode(classified_tokens):

    def resolve_array_index(classified_tokens, index):
                """
                Checks if the tokens starting at `index` form an array-indexing pattern:
                IDENTIFIER [ NUMBER ]
                
                Returns (value, tokens_consumed) if it matches, or (None, 0) if it doesn't,
                and prints an error if the pattern starts correctly but is malformed.
                """
                name_type, name_value = classified_tokens[index]

                if name_type != "IDENTIFIER":
                    return None, 0

                # is the NEXT token a '[' ?
                if index + 1 >= len(classified_tokens):
                    return None, 0

                bracket_type, bracket_value = classified_tokens[index + 1]
                if bracket_value != "[":
                    return None, 0

                # confirmed this is an indexing attempt - now validate it fully
                if name_value not in VARIABLES:
                    print("Runtime Error")
                    print("Unknown Array", name_value)
                    return "ERROR", 0

                array_value = VARIABLES[name_value]

                if not isinstance(array_value, list):
                    print("Runtime Error")
                    print(name_value, "is not an array")
                    return "ERROR", 0

                idx_type, idx_value = classified_tokens[index + 2]
                if idx_type != "NUMBER":
                    print("Grammar Error")
                    print("Expected Number Index")
                    return "ERROR", 0

                close_type, close_value = classified_tokens[index + 3]
                if close_value != "]":
                    print("Grammar Error")
                    print("Expected ']'")
                    return "ERROR", 0

                position = int(idx_value)

                if position < 0 or position >= len(array_value):
                    print("Runtime Error")
                    print("Index", position, "out of range for array", name_value)
                    return "ERROR", 0

                element = array_value[position]

                # tokens consumed: IDENTIFIER [ NUMBER ]  = 4 tokens
                return element, 4

    index = 0
    allowedVarTypes = ["NUMBER", "STRING", "IDENTIFIER"]
    ARITHMETIC_OPERATORS = ["SUM","PRODUCT","CLEAVE","FUSE"]
    COMPARISON_OPERATORS = ["EQUALS","DEFICIT","GRADIENT"]

    while index < len(classified_tokens):
            #assessing the token type and value from tuple 
            token_type,token_value = classified_tokens[index]

            
            if token_value == "INOCULUM":
                onlyDeclaration = False    

                #VARIABLE NAME STORING
                variable_name = classified_tokens[index+1][1]

                #checking var name
                var_type,var_value = classified_tokens[index+1]
                if var_type != "IDENTIFIER":
                    print("Grammar Error")
                    print("Expected Variable Name")
                    return

            
                next_type,next_value = classified_tokens[index+2]
                if next_value == ".":
                    onlyDeclaration = True
                else:
                    onlyDeclaration = False
                
                if not onlyDeclaration:
                    #checking assignment
                    next_type,next_value = classified_tokens[index+2]
                    if next_value != "=":
                        print("Grammar Error")
                        print("Expected '='")
                        return

                    #checking value            
                    value_type,value_value = classified_tokens[index+3]
                    if value_type not in allowedVarTypes:
                        print("Grammar Error")
                        print("Expected Value")
                        return

                    #checking for arthematic ops while declarating           
                    next_type,next_value = classified_tokens[index+4]
                    if next_value in ARITHMETIC_OPERATORS:
                        operator = next_value

                        #checking for right value and is it a value
                        right_type, right_value = classified_tokens[index + 5]
                        if right_type not in allowedVarTypes:
                            print("Grammar Error")
                            print("Expected Right Value")
                            return

                        #chekcing for period
                        next_type,next_value = classified_tokens[index+6]
                        if next_value != ".":
                            print("Grammar Error")
                            print("Expected '.'")
                            return

                        result = evaluate_expression(
                            value_type,
                            value_value,
                            operator,
                            right_value,
                            right_type
                        )

                        VARIABLES[variable_name] = result

                        index += 7
                        continue

                    else:
                        if next_value != ".":
                            print("Grammar Error")
                            print("Expected '.'")
                            return

                        #storing in memory
                        variable_value = classified_tokens[index+3][1]
                        VARIABLES[variable_name] = variable_value

                        index += 5
                        continue
                    
                elif onlyDeclaration:
                    #checking assignment
                    next_type,next_value = classified_tokens[index+2]
                    if next_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return  

                    VARIABLES[variable_name] = None

                    index += 3
                    continue             

            if token_value == "EXCRETION":

                #checking opening brackets 
                next_type,next_value = classified_tokens[index+1]
                if next_value != "(":
                    print("Grammar Error")
                    print("Expected '('")
                    return "ERROR"

                # check if this is an array indexing expression, e.g. scores[0]
                indexed_value, tokens_consumed = resolve_array_index(classified_tokens, index + 2)

                if indexed_value == "ERROR":
                    return "ERROR"

                if tokens_consumed > 0:
                    # it WAS an array index - print the resolved element directly
                    print(indexed_value)

                    # position after: EXCRETION ( scores [ 0 ] ) .
                    after_index = index + 2 + tokens_consumed

                    close_type, close_value = classified_tokens[after_index]
                    if close_value != ")":
                        print("Grammar Error")
                        print("Expected ')'")
                        return "ERROR"

                    period_type, period_value = classified_tokens[after_index + 1]
                    if period_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return "ERROR"

                    index = after_index + 2
                    continue

                #checking var name (ORIGINAL logic, unchanged, runs only if NOT an array index)
                value_type,value_value = classified_tokens[index+2]
                if value_type not in allowedVarTypes:
                    print("Grammar Error")
                    print("Expected Value")
                    return
                
                #checking closing brackets 
                next_type,next_value = classified_tokens[index+3]
                if next_value != ")":
                    print("Grammar Error")
                    print("Expected ')'")
                    return
                
                #checking opening brackets 
                next_type,next_value = classified_tokens[index+4]
                if next_value != ".":
                    print("Grammar Error")
                    print("Expected '.'")
                    return


                #printing/output
                if value_type == "IDENTIFIER":

                    if value_value in VARIABLES:
                        value = VARIABLES[value_value]
                        if isinstance(value, str):
                            if value.startswith('"') and value.endswith('"'):
                                print(value[1:-1])
                            else:
                                print(value)

                        else:
                            print(value)

                    else:
                        print("Logics Error")
                        print("Unknown Variable:",value_value)

                elif value_type == "STRING":
                    print(value_value[1:-1])

                else:
                    print(value_value)
                    
                index += 5
                continue
                    
            if token_value == "RESPIRATE":

                    #checking opening brackets 
                    next_type,next_value = classified_tokens[index+1]
                    if next_value != "(":
                        print("Grammar Error")
                        print("Expected '('")
                        return
                                    
                    #checking var name
                    var_type,var_value = classified_tokens[index+2]
                    if var_type != "IDENTIFIER":
                        print("Grammar Error")
                        print("Expected Variable")
                        return
                                
                    #checking closing brackets 
                    next_type,next_value = classified_tokens[index+3]
                    if next_value != ")":
                        print("Grammar Error")
                        print("Expected ')'")
                        return
                                
                    #checking opening brackets 
                    next_type,next_value = classified_tokens[index+4]
                    if next_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return

                    if var_value not in VARIABLES:
                        print("Runtime Error")
                        print("Unknown Variable", var_value)
                        return

                    user_input = input("Doc: ")

                    VARIABLES[var_value] = user_input

                    index += 5
                    continue

            if token_value == "TRIGGER":

                #for handling elif and else conditions
                chain_handled = False


                #syntax for if statement
                #(
                next_type, next_value = classified_tokens[index + 1]
                if next_value != "(":
                    print("Grammar Error")
                    print("Expected '('")
                    return

                #value 1
                left_type, left_value = classified_tokens[index + 2]
                if left_type not in allowedVarTypes:
                    print("Grammar Error")
                    print("Expected Value")
                    return            

                #comp operator
                operator_type, operator_value = classified_tokens[index + 3]
                if operator_value not in COMPARISON_OPERATORS:
                    print("Grammar Error")
                    print("Expected Comparison Operator")
                    return

                #value 2
                right_type, right_value = classified_tokens[index + 4]
                if right_type not in allowedVarTypes:
                    print("Grammar Error")
                    print("Expected Value")
                    return            

                #)
                next_type, next_value = classified_tokens[index + 5]
                if next_value != ")":
                    print("Grammar Error")
                    print("Expected ')'")
                    return

                #{
                next_type, next_value = classified_tokens[index + 6]
                if next_value != "{":
                    print("Grammar Error")
                    print("Expected '{'")
                    return

                #checking for } in code for trigger code
                block_start = index + 7 
                block_end = block_start
                open_braces = 1

                while open_braces > 0:
                    current_type , current_value = classified_tokens[block_end]

                    if current_value == "{":
                        open_braces += 1
                    elif current_value == "}":
                        open_braces -= 1

                    if open_braces == 0:
                        break

                    block_end += 1

                condition_result = evaluate_condition(
                    left_type,
                    left_value,
                    operator_value,
                    right_value,
                    right_type
                )

                #if condition true so run it in parser again and leave the rest of the code below (stimulus and homeostasis)
                if condition_result:
                    innerTokens = classified_tokens[block_start:block_end]
                    signal = parse_biocode(innerTokens)
                    chain_handled = True
                    if signal == "BREAK" or signal == "CONTINUE" or signal == "ERROR":
                        return signal
                    if isinstance(signal, tuple) and signal[0] == "RETURN":
                        return signal

                #index was on } but for checking its +1 for next token
                index = block_end + 1

                while index < len(classified_tokens) and classified_tokens[index][1] == "STIMULUS":

                    #checking stimulus syntax
                    #(    
                    s_next_type, s_next_value = classified_tokens[index + 1]
                    if s_next_value != "(":
                        print("Grammar Error")
                        print("Expected '('")
                        return
                        
                    #left value
                    s_left_type, s_left_value = classified_tokens[index + 2]
                    if s_left_type not in allowedVarTypes:
                        print("Grammar Error")
                        print("Expected Value")
                        return

                    #operator    
                    s_operator_type, s_operator_value = classified_tokens[index + 3]
                    if s_operator_value not in COMPARISON_OPERATORS:
                        print("Grammar Error")
                        print("Expected Comparison Operator")
                        return

                    #right value
                    s_right_type, s_right_value = classified_tokens[index + 4]
                    if s_right_type not in allowedVarTypes:
                        print("Grammar Error")
                        print("Expected Value")
                        return

                    #)
                    s_next_type, s_next_value = classified_tokens[index + 5]
                    if s_next_value != ")":
                        print("Grammar Error")
                        print("Expected ')'")
                        return

                    #{
                    s_next_type, s_next_value = classified_tokens[index + 6]
                    if s_next_value != "{":
                        print("Grammar Error")
                        print("Expected '{'")
                        return

                    # find this STIMULUS block's matching '}'
                    s_block_start = index + 7
                    s_block_end = s_block_start
                    s_open_braces = 1

                    while s_open_braces > 0:
                        s_current_type, s_current_value = classified_tokens[s_block_end]

                        if s_current_value == "{":
                            s_open_braces += 1
                        elif s_current_value == "}":
                            s_open_braces -= 1

                        if s_open_braces == 0:
                            break

                        s_block_end += 1        

                    #if trigger condition is false then evaluate this else leave it
                    if not(chain_handled):
                        s_condition_result = evaluate_condition(
                            s_left_type,
                            s_left_value,
                            s_operator_value,
                            s_right_value,
                            s_right_type
                        )

                        if s_condition_result:
                            print("Condition TRUE - running block")
                            s_inner_tokens = classified_tokens[s_block_start:s_block_end]
                            signal = parse_biocode(s_inner_tokens)
                            chain_handled = True
                            if signal == "BREAK" or signal == "CONTINUE" or signal == "ERROR":
                                return signal
                            if isinstance(signal, tuple) and signal[0] == "RETURN":
                                return signal

                    #shifting index form stimulus } to next token for checking 
                    index = s_block_end + 1

                if index < len(classified_tokens) and classified_tokens[index][1] == "HOMEOSTASIS":

                    #checking syntax for homeostasis
                    h_next_type, h_next_value = classified_tokens[index + 1]
                    if h_next_value != "{":
                        print("Grammar Error")
                        print("Expected '{'")
                        return

                    #finding the closing curve bracket }
                    h_block_start = index + 2
                    h_block_end = h_block_start
                    h_open_braces = 1

                    while h_open_braces > 0:
                        h_current_type, h_current_value = classified_tokens[h_block_end]

                        if h_current_value == "{":
                            h_open_braces += 1
                        elif h_current_value == "}":
                            h_open_braces -= 1

                        if h_open_braces == 0:
                            break

                        h_block_end += 1

                    
                    #if trigger and stimulus conditions are false then evaluate this else leave it
                    if not chain_handled:
                        print("No earlier condition matched - running HOMEOSTASIS block")
                        h_inner_tokens = classified_tokens[h_block_start:h_block_end]
                        signal = parse_biocode(h_inner_tokens)
                        chain_handled = True
                        if signal == "BREAK" or signal == "CONTINUE" or signal == "ERROR":
                                return signal
                        if isinstance(signal, tuple) and signal[0] == "RETURN":
                                return signal
                        
                    index = h_block_end + 1
                    
                
                continue          

            if token_value == "CATALYST":
                print("Parsing while loop")

                #syntax checking
                #(
                next_type, next_value = classified_tokens[index + 1]
                if next_value != "(":
                    print("Grammar Error")
                    print("Expected '('")
                    return

                #value 1
                left_type, left_value = classified_tokens[index + 2]
                if left_type not in allowedVarTypes:
                    print("Grammar Error")
                    print("Expected Value")
                    return

                #comp operator
                operator_type, operator_value = classified_tokens[index + 3]
                if operator_value not in COMPARISON_OPERATORS:
                    print("Grammar Error")
                    print("Expected Comparison Operator")
                    return

                #value 2
                right_type, right_value = classified_tokens[index + 4]
                if right_type not in allowedVarTypes:
                    print("Grammar Error")
                    print("Expected Value")
                    return

                #)
                next_type, next_value = classified_tokens[index + 5]
                if next_value != ")":
                    print("Grammar Error")
                    print("Expected ')'")
                    return

                #{
                next_type, next_value = classified_tokens[index + 6]
                if next_value != "{":
                    print("Grammar Error")
                    print("Expected '{'")
                    return

                # Step A: Find matching '}'
                block_start = index + 7
                block_end = block_start
                open_braces = 1

                while open_braces > 0:
                    current_type, current_value = classified_tokens[block_end]

                    if current_value == "{":
                        open_braces += 1
                    elif current_value == "}":
                        open_braces -= 1

                    if open_braces == 0:
                        break

                    block_end += 1

                inner_tokens = classified_tokens[block_start:block_end]

                loop_count = 0
                MAX_LOOPS = 100000

                while True:

                    condition_result = evaluate_condition(
                        left_type,
                        left_value,
                        operator_value,
                        right_value,
                        right_type
                    )

                    if not condition_result:
                        break


                    signal = parse_biocode(inner_tokens)
                    if signal == "BREAK":
                        break

                    if signal == "CONTINUE":
                        loop_count += 1
                        if loop_count >= MAX_LOOPS:
                            print("Runtime Error")
                            print("Loop exceeded max iteration limit")
                            break
                        continue
                

                    if signal == "ERROR":
                        break

                    if isinstance(signal, tuple) and signal[0] == "RETURN":
                        return signal

                    loop_count += 1

                    if loop_count >= MAX_LOOPS:
                        print("Runtime Error")
                        print("Loop exceeded max iteration limit")
                        break

                index = block_end + 1 
                continue

            if token_value == "BREAK":

                next_type, next_value = classified_tokens[index + 1]
                if next_value != ".":
                    print("Grammar Error")
                    print("Expected '.'")
                    return "ERROR"

                return "BREAK"

            if token_value == "CONTINUE":

                next_type, next_value = classified_tokens[index + 1]
                if next_value != ".":
                    print("Grammar Error")
                    print("Expected '.'")
                    return "ERROR"   
                
                return "CONTINUE"        

            if token_value == "SYNTHESIZE":
                print("Parsing function declaration")

                # function name
                name_type, name_value = classified_tokens[index + 1]
                if name_type != "IDENTIFIER":
                    print("Grammar Error")
                    print("Expected Function Name")
                    return "ERROR"

                function_name = name_value

                # check what comes after the name - '(' for parameters, or '{' for no parameters
                next_type, next_value = classified_tokens[index + 2]

                param_names = []

                if next_value == "(":
                    # we have a parameter list to parse
                    scan_index = index + 3

                    while True:
                        param_type, param_value = classified_tokens[scan_index]

                        if param_value == ")":
                            # empty parentheses, e.g. SYNTHESIZE greet(){
                            scan_index += 1
                            break

                        if param_type != "IDENTIFIER":
                            print("Grammar Error")
                            print("Expected Parameter Name")
                            return "ERROR"

                        param_names.append(param_value)
                        scan_index += 1

                        # after a parameter name, we expect either ',' (more params) or ')' (done)
                        sep_type, sep_value = classified_tokens[scan_index]

                        if sep_value == ",":
                            scan_index += 1
                            continue
                        elif sep_value == ")":
                            scan_index += 1
                            break
                        else:
                            print("Grammar Error")
                            print("Expected ',' or ')'")
                            return "ERROR"


                    # after the closing ')', we expect '{'
                    brace_type, brace_value = classified_tokens[scan_index]
                    if brace_value != "{":
                        print("Grammar Error")
                        print("Expected '{'")
                        return "ERROR"

                    block_start = scan_index + 1

                elif next_value == "{":
                    # no parameters at all
                    block_start = index + 3

                else:
                    print("Grammar Error")
                    print("Expected '(' or '{'")
                    return "ERROR"

                # find matching '}' for the function body
                block_end = block_start
                open_braces = 1

                while open_braces > 0:
                    current_type, current_value = classified_tokens[block_end]

                    if current_value == "{":
                        open_braces += 1
                    elif current_value == "}":
                        open_braces -= 1

                    if open_braces == 0:
                        break

                    block_end += 1

                function_body = classified_tokens[block_start:block_end]

                # store both params and body together
                FUNCTIONS[function_name] = {
                    "params": param_names,
                    "body": function_body
                }

                print("Function declared:", function_name, "| Parameters:", param_names)

                index = block_end + 1
                continue

            if token_value in FUNCTIONS:
                print("Parsing function call")

                function_info = FUNCTIONS[token_value]
                expected_params = function_info["params"]

                # (
                next_type, next_value = classified_tokens[index + 1]
                if next_value != "(":
                    print("Grammar Error")
                    print("Expected '('")
                    return "ERROR"

                # scan arguments
                argument_values = []
                scan_index = index + 2

                first_type, first_value = classified_tokens[scan_index]

                if first_value == ")":
                    # no arguments, e.g. greet().
                    scan_index += 1
                else:
                    while True:
                        arg_type, arg_value = classified_tokens[scan_index]

                        if arg_type not in allowedVarTypes:
                            print("Grammar Error")
                            print("Expected Argument Value")
                            return "ERROR"

                        # resolve IDENTIFIER arguments to their current value
                        if arg_type == "IDENTIFIER":
                            if arg_value not in VARIABLES:
                                print("Runtime Error")
                                print("Unknown Variable", arg_value)
                                return "ERROR"
                            argument_values.append(VARIABLES[arg_value])
                        else:
                            argument_values.append(arg_value)

                        scan_index += 1

                        sep_type, sep_value = classified_tokens[scan_index]

                        if sep_value == ",":
                            scan_index += 1
                            continue
                        elif sep_value == ")":
                            scan_index += 1
                            break
                        else:
                            print("Grammar Error")
                            print("Expected ',' or ')'")
                            return "ERROR"
                        
                

                # .
                period_type, period_value = classified_tokens[scan_index]
                if period_value != ".":
                    print("Grammar Error")
                    print("Expected '.'")
                    return "ERROR"

                # check argument count matches parameter count
                if len(argument_values) != len(expected_params):
                    print("Runtime Error")
                    print("Function", token_value, "expected", len(expected_params), "arguments but got", len(argument_values))
                    return "ERROR"

                for i in range(len(expected_params)):
                    param_name = expected_params[i]
                    VARIABLES[param_name] = argument_values[i]

                print("Calling function:", token_value, "with arguments:", argument_values)
                signal = parse_biocode(function_info["body"])
                                
                call_result = None
                if isinstance(signal, tuple) and signal[0] == "RETURN":
                    call_result = signal[1]
                    print("Function", token_value, "returned:", call_result)

                index = scan_index + 1
                continue

            if token_type == "IDENTIFIER":

                var_name = token_value

                if var_name not in VARIABLES:
                    print("Runtime Error")
                    print("Unknown Variable",var_name)
                    return

                #checking for =
                next_type, next_value = classified_tokens[index + 1]
                if next_value != "=":
                    print("Grammar Error")
                    print("Expected '='")
                    return

                #CHECKING FOR VALUE
                value_type,value_value = classified_tokens[index + 2]
                if value_type not in allowedVarTypes:
                    print("Grammer Error")
                    print("Expected Value")
                    return

                #ARTHEMATICS WHILE INITIALIZING
                next_type, next_value = classified_tokens[index + 3]
                if next_value in ARITHMETIC_OPERATORS:

                    operator = next_value

                    right_type, right_value = classified_tokens[index + 4]

                    if right_type not in allowedVarTypes:
                        print("Grammar Error")
                        print("Expected Right Value")
                        return

                    next_type, next_value = classified_tokens[index + 5]

                    if next_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return

                    result = evaluate_expression(
                        value_type,
                        value_value,
                        operator,
                        right_value,
                        right_type                )

                    VARIABLES[var_name] = result

                    index += 6
                    continue

                else:

                    if next_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return

                    if value_type == "IDENTIFIER":

                        if value_value not in VARIABLES:
                            print("Runtime Error")
                            print("Unknown Variable:", value_value)
                            return

                        VARIABLES[var_name] = VARIABLES[value_value]

                    else:

                        VARIABLES[var_name] = value_value

                    index += 4
                    continue     

            if token_value == "RETURN":
                print("Parsing return statement")

                # value being returned
                value_type, value_value = classified_tokens[index + 1]
                if value_type not in allowedVarTypes:
                    print("Grammar Error")
                    print("Expected Value")
                    return "ERROR"

                # resolve IDENTIFIER to its actual value
                if value_type == "IDENTIFIER":
                    if value_value not in VARIABLES:
                        print("Runtime Error")
                        print("Unknown Variable", value_value)
                        return "ERROR"
                    return_value = VARIABLES[value_value]
                else:
                    return_value = value_value

                # check for an arithmetic expression, e.g. RETURN a SUM b.
                next_type, next_value = classified_tokens[index + 2]

                if next_value in ARITHMETIC_OPERATORS:
                    operator = next_value

                    right_type, right_value = classified_tokens[index + 3]
                    if right_type not in allowedVarTypes:
                        print("Grammar Error")
                        print("Expected Right Value")
                        return "ERROR"

                    period_type, period_value = classified_tokens[index + 4]
                    if period_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return "ERROR"

                    return_value = evaluate_expression(
                        value_type,
                        value_value,
                        operator,
                        right_value,
                        right_type
                    )

                else:
                    # no arithmetic, just a plain value
                    if next_value != ".":
                        print("Grammar Error")
                        print("Expected '.'")
                        return "ERROR"

                print("RETURN triggered - returning value:", return_value)
                return ("RETURN", return_value)

            if token_value == "INOCULUM_CHAIN":
                print("Parsing array declaration")

                # array name
                name_type, name_value = classified_tokens[index + 1]
                if name_type != "IDENTIFIER":
                    print("Grammar Error")
                    print("Expected Array Name")
                    return "ERROR"

                array_name = name_value

                # =
                next_type, next_value = classified_tokens[index + 2]
                if next_value != "=":
                    print("Grammar Error")
                    print("Expected '='")
                    return "ERROR"

                # [
                next_type, next_value = classified_tokens[index + 3]
                if next_value != "[":
                    print("Grammar Error")
                    print("Expected '['")
                    return "ERROR"

                # scan elements
                array_values = []
                scan_index = index + 4

                first_type, first_value = classified_tokens[scan_index]

                if first_value == "]":
                    # empty array, e.g. INOCULUM_CHAIN scores = [].
                    scan_index += 1
                else:
                    while True:
                        element_type, element_value = classified_tokens[scan_index]

                        if element_type not in allowedVarTypes:
                            print("Grammar Error")
                            print("Expected Array Element")
                            return "ERROR"

                        # resolve IDENTIFIER elements to their current value
                        if element_type == "IDENTIFIER":
                            if element_value not in VARIABLES:
                                print("Runtime Error")
                                print("Unknown Variable", element_value)
                                return "ERROR"
                            array_values.append(VARIABLES[element_value])
                        else:
                            array_values.append(element_value)

                        scan_index += 1

                        sep_type, sep_value = classified_tokens[scan_index]

                        if sep_value == ",":
                            scan_index += 1
                            continue
                        elif sep_value == "]":
                            scan_index += 1
                            break
                        else:
                            print("Grammar Error")
                            print("Expected ',' or ']'")
                            return "ERROR"

                # .
                period_type, period_value = classified_tokens[scan_index]
                if period_value != ".":
                    print("Grammar Error")
                    print("Expected '.'")
                    return "ERROR"

                VARIABLES[array_name] = array_values

                print("Array declared:", array_name, "=", array_values)

                index = scan_index + 1
                continue

            




            #next token to analyse in lab 😉
            index += 1

