import os
import json
import codecs
from pathlib import Path

def should_exclude(path):
    exclude_patterns = [
        '.git', '.vscode', '__pycache__', 'venv', 'env',
        'db.sqlite3', '*.pyc', '*.pyo', '*.pyd', '*.db', 'data_farsi.xlsx',
        'media', 'node_modules', '.DS_Store', 'migrations',
        'jspdf.umd.min.js', 'html2canvas.min.js', 'jquery-3.6.0.min.js', 'jalalidatepicker.min.js',
        'codeBase.json', 'code_base_to_prompt.py', 'jalalidatepicker.min.css', 'media', 'fake_data',
        'logs', 'search2', 'excel_analysis.json', "__init__.py", "manage.py", "requirements.txt", "send_fake_data",
        'docs'
    ]
    
    return any(pattern in path.replace(os.sep, '/') or path.endswith(pattern) for pattern in exclude_patterns)

def is_relevant_static_file(file):
    relevant_extensions = ['.js', '.css', '.html', '.svg']
    return any(file.lower().endswith(ext) for ext in relevant_extensions)

def get_project_structure(start_path):
    structure = {}
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        files = [f for f in files if not should_exclude(os.path.join(root, f))]
        
        if 'static' in root.replace(os.sep, '/'):
            files = [f for f in files if is_relevant_static_file(f)]
        
        path = os.path.relpath(root, start_path).replace(os.sep, '/')
        if path == '.':
            path = ''
        structure[path] = files
    return structure

def read_file_content(file_path):
    try:
        with codecs.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def extract_project(project_path):
    project_structure = get_project_structure(project_path)
    
    output = {
        "structure": project_structure,
        "files_content": {}
    }
    
    for path, files in project_structure.items():
        for file in files:
            full_path = os.path.join(project_path, path, file).replace('/', os.sep)
            if os.path.isfile(full_path):
                relative_path = os.path.join(path, file).replace(os.sep, '/')
                output["files_content"][relative_path] = read_file_content(full_path)
    
    return output

def save_output(output, output_file):
    with codecs.open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    project_path = '.'
    output_file = 'codeBase.json'
    
    project_data = extract_project(project_path)
    save_output(project_data, output_file)
    