import sys
import os
import ast

def get_function_from_file(filename, func_name):
    with open(filename, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            # Compile and execute the function definition
            module = ast.Module(body=[node], type_ignores=[])
            code = compile(module, filename="<string>", mode="exec")
            namespace = {}
            # We need 're' in namespace since the function uses it
            import re
            namespace['re'] = re
            exec(code, namespace)
            return namespace[func_name]
    return None

sourcing_path = os.path.join(os.getcwd(), 'app', 'services', 'sourcing.py')
try:
    extract_price = get_function_from_file(sourcing_path, 'extract_price')
    if not extract_price:
        raise Exception("Function not found")
except Exception as e:
    print(f"Error extracting function: {e}")
    sys.exit(1)

test_cases = [
    "£13.95",
    "£ 13.95",
    "Price: £10.00",
    "13.95",
    "1,200.50",
    "Citra Hops 100g - £7.50",
    "From £5.00 to £10.00",
    "7.50 GBP",
    "Price: 7.50 GBP",
    "Cost: 5.99", 
    "snippet with no price"
]

print("Verifying app.services.sourcing.extract_price:")
for t in test_cases:
    print(f"'{t}' -> {extract_price(t)}")
