<?php
ini_set('display_errors', 'stderr');


$f = fopen($argv[1], "r");

$err22msg = "Neznamy nebo chybny operacni kod ve zdrojovem kodu zapsanem v IPPcode21.\n";
$err23msg = "Lexikalni nebo syntakticka chyba zdrojoveho kodu zapsaneho v IPPcode21.\n";

function line_arrange($l)
{
    $l = preg_replace('/#(.)*/', ' ', $l);  // Remove comments
    $l = preg_replace('/\s+/', ' ', $l);    // Remove extra spaces
    $l = trim($l);                          // Remove spaces from the beginning and end of a line

    return $l;
}

function p_var($var)
{
    return preg_match('/^(GF|TF|LF)@([a-z]|[A-Z]|_|-|\$|&|%|\*|!|\?)(\w|-|\$|&|%|\*|!|\?)*$/', $var);
}

function p_const($const)
{
    if(preg_match('/^(int|string|bool|nil)@.*$/', $const)) {
        if(preg_match('/^string@/', $const)) {
            return !preg_match('/\\\(\D|\d(\D|$)|\d\d(\D|$)|$)/', $const);  // Check for correct escape sequences
        } elseif(preg_match('/^bool@/', $const)) {
            return preg_match('/^bool@true$|^bool@false$/', $const);        // Only bool@true and bool@false is allowed
        } elseif(preg_match('/^nil@/', $const)) {
            return preg_match('/^nil@nil$/', $const);                       // Only nil@nil is allowed
        } else {
            return true;    
        }
    } else {
        return false;
    }
}

function p_label($label)
{
    return preg_match('/^([a-z]|[A-Z]|_|-|\$|&|%|\*|!|\?)(\w|-|\$|&|%|\*|!|\?)*$/', $label);
}

function p_type($type)
{
    return preg_match('/^(int|string|bool|nil)$/', $type);
}

function instr_get_type($instr, $instr_arg) 
{
    if(strncmp($instr_arg, "GF@", 3) == 0 || strncmp($instr_arg, "LF@", 3) == 0 || strncmp($instr_arg, "TF@", 3) == 0) {
        return "var";
    } elseif(strncmp($instr_arg, "int@", 4) == 0) {
        return "int";
    } elseif(strncmp($instr_arg, "string@", 7) == 0) {
        return "string";
    } elseif(strncmp($instr_arg, "bool@", 5) == 0) {
        return "bool";
    } elseif(strncmp($instr_arg, "nil@", 4) == 0) {
        return "nil";
    } elseif(($instr_arg == "int" || $instr_arg == "string" || $instr_arg == "bool" || $instr_arg == "nil") && $instr == "READ") {
        // Only within READ instruction
        // Label name can contain keyword with type "type"
        return "type";
    } else {
        return "label";
    }
}

function instr_get_text($instr_arg) 
{
    if(p_const($instr_arg)) {       // Use substring after '@' character
        return substr($instr_arg, strpos($instr_arg, '@') + 1);
    } else {
        return $instr_arg;
    }
}

/**     XML generate     **/
$xw = xmlwriter_open_memory();
xmlwriter_set_indent($xw, 1);
$res = xmlwriter_set_indent_string($xw, ' ');

xmlwriter_start_document($xw, '1.0', 'UTF-8');
xmlwriter_start_element($xw, 'program');        // Start program element

// language attribute 
xmlwriter_start_attribute($xw, 'language');
xmlwriter_text($xw, 'IPPcode21');
xmlwriter_end_attribute($xw);

$header = false;    // '.IPPcode21'
$order = 0;         // Instruction order

while ($l = fgets($f)) {

    if ($l != "\r\n") {
        $l = line_arrange($l);

        $arr = explode(" ", trim($l, "\n"));        // Split a line into substrings, remove newline char
        $arr[0] = strtoupper($arr[0]);              // Convert opcode to uppercase 
        if (strlen($l) > 0) {   // In case there is a line with comment only, empty array remains 
            switch ($arr[0]) {
                case '.IPPCODE21':
                    if($order == 0) {
                        $header = true;
                    } else {
                        fprintf(STDERR, "Chybejici hlavicka .IPPcode21\n");
                        exit(21);
                    }
                    break;
                
                case 'CREATEFRAME':         // opcode </>
                case 'PUSHFRAME':
                case 'POPFRAME':
                case 'RETURN':
                case 'BREAK':
                    if (count($arr) != 1) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'DEFVAR':              // opcode <var>
                case 'POPS':
                    if (count($arr) != 2) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_var($arr[1])) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'PUSHS':               // opcode <symb>
                case 'WRITE':
                case 'EXIT':
                case 'DPRINT':

                    if (count($arr) != 2) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_var($arr[1]) && !p_const($arr[1])) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'CALL':               // opcode <label>
                case 'LABEL':
                case 'JUMP':
                    if (count($arr) != 2) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_label($arr[1])) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'MOVE':               // opcode <var> <symb>
                case 'INT2CHAR':
                case 'STRLEN':
                case 'TYPE':
                case 'NOT':
                    if (count($arr) != 3) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_var($arr[1]) || (!p_var($arr[2]) && !p_const($arr[2]))) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'READ':              // opcode <var> <type>
                    if (count($arr) != 3) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_var($arr[1]) || !p_type($arr[2])) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'ADD':               // opcode <var> <symb> <symb>
                case 'SUB':
                case 'MUL':
                case 'IDIV':
                case 'LT':
                case 'GT':
                case 'EQ':
                case 'AND':
                case 'OR':
                case 'STRI2INT':
                case 'CONCAT':
                case 'GETCHAR':
                case 'SETCHAR':
                    if (count($arr) != 4) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_var($arr[1]) || (!p_var($arr[2]) && !p_const($arr[2])) || (!p_var($arr[3]) && !p_const($arr[3]))) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                case 'JUMPIFEQ':           // opcode <label> <symb> <symb>
                case 'JUMPIFNEQ':
                    if (count($arr) != 4) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    if (!p_label($arr[1]) || (!p_var($arr[2]) && !p_const($arr[2])) || (!p_var($arr[3]) && !p_const($arr[3]))) {
                        fprintf(STDERR, $err23msg);
                        exit(23);
                    }
                    break;

                default:
                    if(!$header) {
                        fprintf(STDERR, $err21msg);
                        exit(21);
                    } else {
                        fprintf(STDERR, $err22msg);
                        exit(22);
                    }
            }

            if($order > 0) {      // Starting after header is processed 
                xmlwriter_start_element($xw, 'instruction');     // Start instruction element

                // order attribute 
                xmlwriter_start_attribute($xw, 'order');
                xmlwriter_text($xw, "$order");
                xmlwriter_end_attribute($xw);

                // opcode attribute
                xmlwriter_start_attribute($xw, 'opcode');
                xmlwriter_text($xw, $arr[0]);
                xmlwriter_end_attribute($xw);

                for($j=1; $j<count($arr); $j++) {
                    xmlwriter_start_element($xw, "arg$j");      // Start arg element
                    // type attribute
                    xmlwriter_start_attribute($xw, 'type'); 
                    xmlwriter_text($xw, instr_get_type($arr, $arr[$j]));
                    xmlwriter_end_attribute($xw);
                   
                    xmlwriter_text($xw, instr_get_text($arr[$j]));
                    xmlwriter_end_element($xw);                 // End arg element 
                    
                }
                xmlwriter_end_element($xw);         // End instruction element
            }
            $order++;     // Increment instruction counter
        }
    }
}
if(!$header) {
    fprintf(STDERR, $err21msg);
    exit(21);
}
xmlwriter_end_element($xw);     // End program element
xmlwriter_end_document($xw);    
echo xmlwriter_output_memory($xw);  // Print XML output
