""" 
--- IPP uloha 2 - Interpret jazyka IPPcode21
--- Autor: Vasil Poposki
--- Datum: Duben 2021
"""
import re
import sys
import xml.etree.ElementTree as ET

# Zpracovani vstupnich argumentu
if not 1 < len(sys.argv) < 4:
    print('Input parameters error')
    exit(10)
if sys.argv[1] == '--help':
    print('Usage:\npython3 interpet.py [--source=file] [--input=file]\n')
    exit(0)

# Nacteni source a input souboru 
xml_data = ''
input_file = ''
for p in sys.argv[1:]:
    if re.match(r'^--source=.+$', p):
        xml_data = re.sub(r'^--source=', '', p)
    elif re.match(r'^--input=.+$', p):
        input_file = re.sub(r'^--input=', '', p)
    else:
        print('ERROR: Chybni vstupni argument')
        exit(10)
if not input_file:
    input_data = sys.stdin.readlines()
    input_data = [line.rstrip() for line in input_data]
else:
    try:
        f = open(input_file, 'r')
    except:
        print('Nepodarilo se otevrit soubor:', input_file)
        exit(11)
    input_data = [line.rstrip() for line in f]
if not xml_data:
    for line in sys.stdin:
        if line == '\n':
            break
        xml_data += line
    try: # Parsovani XML-a z retezce
        tree = ET.fromstring(xml_data)
    except:
        print('ERROR: Spatny format XML')
        exit(31)
else:
    try:
        f = open(xml_data, 'r')
    except:
        print('Nepodarilo se otevrit soubor:', xml_data)
        exit(11)
    try: # Parsovani XML-a ze souboru 
        tree = ET.parse(f)
    except:
        print('ERROR: Spatny format XML')
        exit(31)

class Argument:
    # Trida pro jednotlivy operand instrukce
    def __init__(self, arg_type, arg_value):
        self.arg_type = arg_type
        self.arg_value = arg_value

    def conv_string(self):
        """ Provadi konverzi escape sekvenci v IPPcode na jednotlive ASCII znaky
        """
        if not self.arg_value:
            self.arg_value = ''
        else:
            matches = re.findall(r'\\(0([0-3][0-9]|92))', self.arg_value)  # Vsechny nalezene escape sekvence v argumentu
            for es in matches:
                patt = '\\' + es[0]
                regex = r'' + re.escape(patt) + r''  # Modifikovany regex pro escape sekvenci  
                conv = chr(int(es[1]))               # Hodnota pro zamenu
                if conv == '\\':
                    conv += '\\'
                self.arg_value = re.sub(regex, conv, self.arg_value)    

    def check_type(self):
        """ Kontrola typu operandu
            Vraci True pokud hodnota odpovida typu
        """
        if self.arg_type['type'] == 'var' and not re.search(r'^(GF|LF|TF)@([a-z]|[A-Z]|_|-|\$|&|%|\*|!|\?)(\w|-|\$|&|%|\*|!|\?)*$', self.arg_value):
            return False
        elif self.arg_type['type'] == 'int' and not re.search(r'^-?[0-9]+$', self.arg_value):
            return False
        elif self.arg_type['type'] == 'bool' and not re.search(r'^(true|false)$', self.arg_value):
            return False
        elif self.arg_type['type'] == 'string':
            self.conv_string()          # Proved konverzi retezce
            return True
        elif self.arg_type['type'] == 'nil' and not re.search(r'^nil$', self.arg_value):
            return False
        else:
            return True

class Instruction:
    # Trida instrukce
    def __init__(self, name, order):
        self.name = name
        self.order = order
        self.args = []

    def instr_argument(self, arg_type, arg_value):
        """ Pridani dalsiho argumentu do seznamu argumentu instrukce
        """
        self.args.append(Argument(arg_type, arg_value))
    
    def instr_valid(self):
        """ Kontrola vstupniho XML souboru
            Syntakticka/ lexikalni analyza
        """
        symlist = ['var', 'int', 'string', 'bool', 'nil']
        
        if self.name == 'MOVE':
            if len(self.args) != 2:
                return False
            if self.args[0].arg_type['type'] == 'var' and self.args[1].arg_type['type'] in symlist:
                for a in self.args:
                    if not a.check_type():
                        return False
            else:
                return False

        elif self.name in ['DEFVAR', 'POPS']:
            if len(self.args) != 1:
                return False
            if self.args[0].arg_type['type'] == 'var':
                if not self.args[0].check_type():
                    return False
            else:
                return False

        elif self.name in ['CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'RETURN']:
            if len(self.args) != 0:
                return False
        
        elif self.name == 'READ':
            if len(self.args) != 2:
                return False
            if not self.args[0].check_type():
                return false

        elif self.name in ['WRITE', 'EXIT', 'PUSHS']:
            if len(self.args) != 1:
                return False
            if self.args[0].arg_type['type'] in symlist:
                if not self.args[0].check_type():
                    return False
            else:
                return False

        elif self.name in ['LABEL', 'CALL', 'JUMP']:
            if len(self.args) != 1 or self.args[0].arg_type['type'] != 'label':
                return False
            if self.args[0].arg_type['type'] == 'label':
                if not self.args[0].check_type():
                    return False
            else:
                return False

        elif self.name in ['ADD', 'SUB', 'MUL', 'IDIV', 'LT', 'GT', 'EQ', 'AND', 'OR', 'STRI2INT', 'CONCAT', 'GETCHAR', 'SETCHAR']:
            if len(self.args) != 3:
                return False
            if self.args[0].arg_type['type'] == 'var' and (self.args[1].arg_type['type'] and self.args[2].arg_type['type'] in symlist):
                for a in self.args:
                    if not a.check_type():
                        return False
            else:
                return False
        
        elif self.name in ['NOT', 'INT2CHAR', 'STRLEN', 'TYPE']:
            if len(self.args) != 2:
                return False
            if self.args[0].arg_type['type'] == 'var' and self.args[1].arg_type['type'] in symlist:
                for a in self.args:
                    if not a.check_type():
                        return False
            else:
                return False

        elif self.name in ['JUMPIFEQ', 'JUMPIFNEQ']:
            if len(self.args) != 3:
                return False
            if self.args[0].arg_type['type'] == 'label' and (self.args[1].arg_type['type'] and self.args[2].arg_type['type'] in symlist):
                for a in self.args:
                    if not a.check_type():
                        return False
            else:
                return False
        else:
            return False

        return True

def xml_control(root):
    """ Kontrola formatu XML souboru
    Vraci novy modifikovany koren  
    """
    if root.tag != 'program' or not 'language' in root.attrib or root.attrib['language'] != 'IPPcode21':
        return 32
    try:
        root = sorted(root, key=lambda child:int(child.attrib['order'])) # Serad instrukce dle poradi 'order'
    except:
        return 32

    order_before = 0
    for child in root:
        if child.tag != 'instruction':
            return 32
        instr_attribs = child.attrib.keys()
        if not 'order' in instr_attribs or not 'opcode' in instr_attribs:
            return 32
        if int(child.attrib['order']) < 1 or order_before == child.attrib['order']: 
            return 32
        
        args_cnt = 0
        for subelem in child:
            args_cnt += 1
            regex = r'^arg' + str(args_cnt) + r'$'
            if not re.match(regex, subelem.tag):
                return 32
        order_before = child.attrib['order']
    return root

def input_getdata(pos, arg_type):
    """  Vraci data pro interpretaci instrukce READ
    """
    if len(input_data) <= pos:  # Chybejici hodnota pro READ
        return -1               # Nahrazeno hodnotou 'nil'
    if arg_type == 'int':
        try:
            data = int(input_data[pos])
        except ValueError:
            return -1
        return input_data[pos]
    elif arg_type == 'string':
        return input_data[pos]
    elif arg_type == 'bool':
        if re.match(r'^true$', input_data[pos], re.IGNORECASE):
            return 'true'
        else:
            return 'false'
    else:
        return -1
    
def label_order(label_name):
    """ Vraci pozici navesti v programu
    """
    index = 0
    for i in instructions:
        if i.name == 'LABEL' and i.args[0].arg_value == label_name:
            return index
        index += 1
    return -1

def interpret():
    """ Interpretace jednotlivych instrukci
    Vraci 0 nebo chybu 52-58 
    """
    var_dict = {}
    types_dict = {}
    cnt = 0
    callstack = []
    read_cnt = 0
    label_list = []
    while cnt < len(instructions):
        i = instructions[cnt]

        if i.name == 'JUMP':
            label = i.args[0].arg_value
            l_order = label_order(label)
            if l_order == -1:  # Navesti neni definovano
                return 52 
            
            cnt = l_order - 1

        if i.name == 'JUMPIFEQ' or i.name == 'JUMPIFNEQ':
            label = i.args[0].arg_value
            l_order = label_order(label)
            if l_order == -1:
                return 52

            arg2_type = ''
            arg3_type = ''
            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56      # Neinicializovana promenna
                arg2_type = types_dict[i.args[1].arg_value]
                arg2 = var_dict[i.args[1].arg_value]
            else:
                arg2_type = i.args[1].arg_type['type']
                arg2 = i.args[1].arg_value
            if i.args[2].arg_type['type'] == 'var':
                if not i.args[2].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[2].arg_value]:
                    return 56 
                arg3_type = types_dict[i.args[2].arg_value]
                arg3 = var_dict[i.args[2].arg_value]
            else:
                arg3_type = i.args[2].arg_type['type']
                arg3 = i.args[2].arg_value

            if arg2_type != arg3_type and (arg2_type != 'nil' and arg3_type != 'nil'):
                return 53     # Porovnani typu

            arg2 = str(arg2)
            arg3 = str(arg3)
            if i.name == 'JUMPIFEQ':
                if arg2 == arg3:
                    cnt = l_order - 1
            else:   # JUMPIFNEQ
                if arg2 != arg3:
                    cnt = l_order - 1

        if i.name == 'EXIT':
            arg1 = i.args[0].arg_value
            if i.args[0].arg_type['type'] == 'var': 
                if not arg1 in var_dict:
                    return 54
                if not types_dict[arg1]:
                    return 56 
                if types_dict[arg1] != 'int':
                    return 53
                exitval = int(var_dict[arg1])
            elif i.args[0].arg_type['type'] == 'int':
                exitval = int(arg1)
            else:
                return 53

            if 0 <= exitval <= 49:
                exit(exitval)
            else:   # Chyba
                return 57

        if i.name == 'CALL':
            callstack.append(cnt)
            label = i.args[0].arg_value
            l_order = label_order(label)
            if l_order == -1:
                return 52 # Navesti neexistuje

            cnt = l_order - 1

        if i.name == 'RETURN':
            if(len(callstack) == 0):
                return 56
            cnt = callstack[-1]
            callstack.pop()

        if i.name == 'READ':
            arg1 = i.args[0].arg_value
            arg2 = i.args[1].arg_value
            if not arg1 in var_dict:
                return 54
            data = input_getdata(read_cnt, arg2)
            if data == -1:
                var_dict[arg1] = 'nil'
                types_dict[arg1] = 'nil'
            else:
                var_dict[arg1] = data
                types_dict[arg1] = arg2
            read_cnt += 1
            
        if i.name == 'WRITE':
            arg1 = i.args[0].arg_value
            if i.args[0].arg_type['type'] == 'var':
                if not arg1 in var_dict:
                    return 54
                if not types_dict[arg1]:
                    return 56
                print(var_dict[arg1], end='')
            else:
                print(arg1, end='')

        if i.name == 'TYPE':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54
            if i.args[1].arg_type['type'] == 'var':
                arg2 = i.args[1].arg_value
                if not arg2 in var_dict:
                    return 54
                if not types_dict[arg1]:
                    var_dict[arg1] = ''
                else:
                    var_dict[arg1] = types_dict[arg2]
                types_dict[arg1] = 'string'
            else:
                var_dict[arg1] = i.args[1].arg_type['type']
                types_dict[arg1] = 'string'

        if i.name == 'DEFVAR':
            arg1 = i.args[0].arg_value
            if arg1 in var_dict:
                return 52           # Redefinice promenne
            var_dict[arg1] = ''
            types_dict[arg1] = None
        
        if i.name == 'MOVE':
            arg1 = i.args[0].arg_value 
            if not arg1 in var_dict:
                return 54
            arg2 = i.args[1].arg_value
            if i.args[1].arg_type == 'var':     # Promenna 
                if not arg2 in var_dict:
                    return 54
                var_dict[arg1] = var_dict[arg2]
                types_dict[arg1] = types_dict[arg2]
            else:                               # Konstanta
                var_dict[arg1] = arg2
                types_dict[arg1] = i.args[1].arg_type['type']

        if i.name == 'ADD':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54
            
            for a in i.args[1:]:
                if a.arg_type['type'] == 'var':
                    if not a.arg_value in var_dict:
                        return 54
                    elif not types_dict[a.arg_value]:
                        return 56 
                    elif types_dict[a.arg_value] != 'int':
                        return 53
                else:
                    if a.arg_type['type'] != 'int':
                        return 53
            arg2 = int(var_dict[i.args[1].arg_value]) if i.args[1].arg_type['type'] == 'var' else int(i.args[1].arg_value)
            arg3 = int(var_dict[i.args[2].arg_value]) if i.args[2].arg_type['type'] == 'var' else int(i.args[2].arg_value)

            var_dict[arg1] = arg2 + arg3
            types_dict[arg1] = 'int'
        
        if i.name == 'SUB':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54
            for a in i.args[1:]:
                if a.arg_type['type'] == 'var':
                    if not a.arg_value in var_dict:
                        return 54
                    elif not types_dict[a.arg_value]:
                        return 56 
                    elif types_dict[a.arg_value] != 'int':
                        return 53
                else:
                    if a.arg_type['type'] != 'int':
                        return 53
            arg2 = int(var_dict[i.args[1].arg_value]) if i.args[1].arg_type['type'] == 'var' else int(i.args[1].arg_value)
            arg3 = int(var_dict[i.args[2].arg_value]) if i.args[2].arg_type['type'] == 'var' else int(i.args[2].arg_value)

            var_dict[arg1] = arg2 - arg3
            types_dict[arg1] = 'int'
        
        if i.name == 'MUL':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54
            
            for a in i.args[1:]:
                if a.arg_type['type'] == 'var':
                    if not a.arg_value in var_dict:
                        return 54
                    elif not types_dict[a.arg_value]:
                        return 56 
                    elif types_dict[a.arg_value] != 'int':
                        return 53
                else:
                    if a.arg_type['type'] != 'int':
                        return 53
            arg2 = int(var_dict[i.args[1].arg_value]) if i.args[1].arg_type['type'] == 'var' else int(i.args[1].arg_value)
            arg3 = int(var_dict[i.args[2].arg_value]) if i.args[2].arg_type['type'] == 'var' else int(i.args[2].arg_value)

            var_dict[arg1] = arg2 * arg3
            types_dict[arg1] = 'int'
        
        if i.name == 'IDIV':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            for a in i.args[1:]:
                if a.arg_type['type'] == 'var':
                    if not a.arg_value in var_dict:
                        return 54
                    elif not types_dict[a.arg_value]:
                        return 56 
                    elif types_dict[a.arg_value] != 'int':
                        return 53
                else:
                    if a.arg_type['type'] != 'int':
                        return 53
            arg2 = int(var_dict[i.args[1].arg_value]) if i.args[1].arg_type['type'] == 'var' else int(i.args[1].arg_value)
            arg3 = int(var_dict[i.args[2].arg_value]) if i.args[2].arg_type['type'] == 'var' else int(i.args[2].arg_value)

            if arg3 != 0: 
                var_dict[arg1] = arg2 // arg3 
                types_dict[arg1] = 'int'
            else:
                return 57
        
        if i.name == 'LT' or i.name == 'GT' or i.name == 'EQ':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            arg2_type = ''
            arg3_type = ''
            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                arg2_type = types_dict[i.args[1].arg_value]
                if arg2_type == 'int':
                    arg2 = int(var_dict[i.args[1].arg_value])
                else:
                    arg2 = var_dict[i.args[1].arg_value]
            else:
                arg2_type = i.args[1].arg_type['type']
                if arg2_type == 'nil' and i.name != 'EQ':
                    return 53
                elif arg2_type == 'int':
                    arg2 = int(i.args[1].arg_value)
                else:
                    arg2 = i.args[1].arg_value
            if i.args[2].arg_type['type'] == 'var':
                if not i.args[2].arg_value in var_dict:
                    return 53
                if not types_dict[i.args[2].arg_value]:
                    return 56
                arg3_type = types_dict[i.args[2].arg_value]
                if arg3_type == 'int':
                    arg3 = int(var_dict[i.args[2].arg_value])
                else:
                    arg2 = var_dict[i.args[1].arg_value]
            else:
                arg3_type = i.args[2].arg_type['type']
                if arg3_type == 'nil' and i.name != 'EQ':
                    exit(53)
                elif arg3_type == 'int':
                    arg3 = int(i.args[2].arg_value)
                else:
                    arg3 = i.args[2].arg_value

            if arg2_type != arg3_type:      # arg2 a arg3 musi byt stejneho typu
                return 53

            if i.name == 'LT':
                var_dict[arg1] = 'true' if arg2 < arg3 else 'false'
            elif i.name == 'GT':
                var_dict[arg1] = 'true' if arg2 > arg3 else 'false'
            else:   # EQ
                var_dict[arg1] = 'true' if arg2 == arg3 else 'false'

            types_dict[arg1] = 'bool'

        if i.name == 'AND' or i.name == 'OR' or i.name == 'NOT':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'bool':
                    return 53
                arg2 = True if var_dict[i.args[1].arg_value] == 'true' else False
            elif i.args[1].arg_type['type'] == 'bool':
                arg2 = True if i.args[1].arg_value == 'true' else False
            else:
                return 53
            if i.name != 'NOT':
                if i.args[2].arg_type['type'] == 'var':
                    if not i.args[2].arg_value in var_dict:
                        return 54
                    if not types_dict[i.args[2].arg_value]:
                        return 56
                    if types_dict[i.args[2].arg_value] != 'bool':
                        return 53
                    arg3 = True if var_dict[i.args[2].arg_value] == 'true' else False
                elif i.args[2].arg_type['type'] == 'bool':
                    arg3 = True if i.args[2].arg_value == 'true' else False
                else:
                    return 53

            if i.name == 'AND':
                var_dict[arg1] = 'true' if (arg2 and arg3) else 'false'
            elif i.name == 'OR':
                var_dict[arg1] = 'true' if (arg2 or arg3) else 'false'
            else:   # NOT
                var_dict[arg1] = 'true' if (not arg2) else 'false'

            types_dict[arg1] = 'bool'

        if i.name == 'INT2CHAR':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'int':
                    return 53
                arg2 = int(var_dict[i.args[1].arg_value])
            else:
                arg2 = int(i.args[1].arg_value)
            
            try:
                var_dict[arg1] = chr(arg2)
                types_dict[arg1] = 'string'
            except ValueError:
                exit(58)

        if i.name == 'STRI2INT':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'string':
                    return 53
                arg2 = var_dict[i.args[1].arg_value]
            else:
                arg2 = i.args[1].arg_value
            if i.args[2].arg_type['type'] == 'var':
                if not i.args[2].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[2].arg_value]:
                    return 56
                if types_dict[i.args[2].arg_value] != 'int':
                    return 53
                arg3 = int(var_dict[i.args[2].arg_value])
            else:
                arg3 = int(i.args[2].arg_value)
            
            try:
                var_dict[arg1] = ord(arg2[arg3])
                types_dict[arg1] = 'int'
            except IndexError:
                exit(58)

        if i.name == 'CONCAT':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'string':
                    return 53
                arg2 = var_dict[i.args[1].arg_value]
            elif i.args[1].arg_type['type'] == 'string':
                arg2 = i.args[1].arg_value
            else:
                return 53

            if i.args[2].arg_type['type'] == 'var':
                if not i.args[2].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[2].arg_value]:
                    return 56
                if types_dict[i.args[2].arg_value] != 'string':
                    return 53
                arg3 = var_dict[i.args[2].arg_value]
            elif i.args[2].arg_type['type'] == 'string':
                arg3 = i.args[2].arg_value
            else:
                return 53

            var_dict[arg1] = arg2 + arg3
            types_dict[arg1] = 'string'

        if i.name == 'STRLEN':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'string':
                    return 53
                arg2 = var_dict[i.args[1].arg_value]
            elif i.args[1].arg_type['type'] == 'string':
                arg2 = i.args[1].arg_value
            else:
                return 53

            var_dict[arg1] = len(arg2)
            types_dict[arg1] = 'int'

        if i.name == 'GETCHAR':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'string':
                    return 53
                arg2 = var_dict[i.args[1].arg_value]
            elif i.args[1].arg_type['type'] == 'string':
                arg2 = i.args[1].arg_value
            else:
                return 53

            if i.args[2].arg_type['type'] == 'var':
                if not i.args[2].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[2].arg_value]:
                    return 56
                if types_dict[i.args[2].arg_value] != 'int':
                    return 53
                arg3 = int(var_dict[i.args[2].arg_value])
            elif i.args[2].arg_type['type'] == 'int':
                arg3 = int(i.args[2].arg_value)
            else:
                return 53

            try:
                var_dict[arg1] = arg2[arg3]
                types_dict[arg1] = 'string'
            except IndexError:
                return 58

        if i.name == 'SETCHAR':
            arg1 = i.args[0].arg_value
            if not arg1 in var_dict:
                return 54
            if not types_dict[arg1]:
                return 56
            if types_dict[arg1] != 'string':
                return 53

            if i.args[1].arg_type['type'] == 'var':
                if not i.args[1].arg_value in var_dict:
                    return 54
                if not types_dict[i.args[1].arg_value]:
                    return 56
                if types_dict[i.args[1].arg_value] != 'int':
                    return 53
                arg2 = int(var_dict[i.args[1].arg_value])
            elif i.args[1].arg_type['type'] == 'int':
                arg2 = int(i.args[1].arg_value)
            else:
                return 53

            if i.args[2].arg_type['type'] == 'var':
                if not i.args[2].arg_value in var_dict:
                    return 54
                if types_dict[i.args[2].arg_value] != 'string':
                    return 53
                if not types_dict[i.args[2].arg_value]:
                    return 56
                arg3 = var_dict[i.args[2].arg_value]
            elif i.args[2].arg_type['type'] == 'string':
                arg3 = i.args[2].arg_value
            else:
                return 53

            try:
                temp = list(var_dict[arg1])
                temp[arg2] = arg3[0]
                var_dict[arg1] = ''.join(temp)
            except:
                return 58
        cnt += 1

root = tree.getroot()
ret_xml_control = xml_control(root)
if ret_xml_control == 31:
    print('ERROR: Chybni XML format')
    exit(31)
elif ret_xml_control == 32:
    print('ERROR: Neocekavana struktura XML')
    exit(32)
else:
    root = ret_xml_control

instructions = []
for child in root:
    instr = Instruction(child.attrib['opcode'], child.attrib['order'])
    for subelem in child:
        instr.instr_argument(subelem.attrib, subelem.text)
    if not instr.instr_valid():
        print('ERROR: Chybni typ/lexem pro literal nebo neznamy operacni kod')
        exit(32)
    instructions.append(instr)

ret_interpret = interpret()
if ret_interpret == 52:
    print('ERROR: Semanticka chyba')
    exit(52)
elif ret_interpret == 53:
    print('ERROR: Spatne typy operandu')
    exit(53)
elif ret_interpret == 54:
    print('ERROR: Pristup k neexistujici promenne')
    exit(54)
elif ret_interpret == 55:
    print('ERROR: Ramec neexistuje')
    exit(55)
elif ret_interpret == 56:
    print('ERROR: Chybejici hodnota(v promenne, na datovem zasobniku nebo v zasobniku volani)')
    exit(56)
elif ret_interpret == 57:
    print('ERROR: Spatna hodnota operandu(deleni nulou nebo spatna navratova hodnota instrukce EXIT)')
    exit(57)
elif ret_interpret == 58:
    print('ERROR: Chybna prace s retezcem')
    exit(58)
else:
    exit(0)