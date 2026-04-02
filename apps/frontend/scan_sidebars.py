import os
import re

page_dir = r"c:\LEARNING\TechnoMax\arogyaai\apps\frontend\src\pages"

def scan_files():
    hits = 0
    for root, dirs, files in os.walk(page_dir):
        for f in files:
            if not (f.endswith('.jsx') or f.endswith('.tsx')):
                continue
                
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                has_aside = '<aside' in content
                has_appsidebar = '<AppSidebar' in content
                has_sidebar = '<Sidebar' in content and not 'Sidebar.' in content  # basic check
                
                if has_aside or has_appsidebar or has_sidebar:
                    print(f"Found in {f}: aside={has_aside}, AppSidebar={has_appsidebar}, Sidebar={has_sidebar}")
                    hits += 1

    print(f"Total files with sidebars: {hits}")

if __name__ == "__main__":
    scan_files()
