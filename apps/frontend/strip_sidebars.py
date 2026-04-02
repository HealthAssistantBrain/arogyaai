import os
import re

page_dir = r"c:\LEARNING\TechnoMax\arogyaai\apps\frontend\src\pages"

def remove_aside(content):
    start_index = content.find('<aside')
    if start_index == -1:
        return content, False

    count = 0
    i = start_index
    while i < len(content):
        next_open = content.find('<aside', i)
        next_close = content.find('</aside>', i)

        if next_close == -1:
            break

        if next_open != -1 and next_open < next_close:
            count += 1
            i = next_open + 6
        else:
            count -= 1
            i = next_close + 8
            if count == 0:
                # To cleanly remove whitespace before it
                before = content[:start_index].rstrip(' \t')
                if before.endswith('\n'):
                    pass # Keep the newline
                return before + content[i:], True

    return content, False

def strip_files():
    modified = 0
    for root, dirs, files in os.walk(page_dir):
        for f in files:
            if not (f.endswith('.jsx') or f.endswith('.tsx')):
                continue
                
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            new_content, changed1 = remove_aside(content)
            
            # also remove any <Sidebar /> or <AppSidebar /> just in case
            new_content, changed2 = re.subn(r'<Sidebar\b[^>]*/>', '', new_content)
            new_content, changed3 = re.subn(r'<AppSidebar\b[^>]*/>', '', new_content)
            
            changed2 = changed2 > 0
            changed3 = changed3 > 0
            
            if changed1 or changed2 or changed3:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f"Modified {f}")
                modified += 1

    print(f"Total files modified: {modified}")

if __name__ == "__main__":
    strip_files()
