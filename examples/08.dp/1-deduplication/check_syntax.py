
import json
import ast

notebook_path = 'c:/_cmps460-content/examples/03.dp/1-deduplication/drop_duplicates.ipynb'

try:
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])
            print(f"Checking cell {i}...")
            try:
                ast.parse(source)
                print(f"Cell {i} is valid.")
            except SyntaxError as e:
                print(f"Syntax error in cell {i}: {e}")
                print("Source code:")
                print(source)

except Exception as e:
    print(f"Error reading notebook: {e}")
