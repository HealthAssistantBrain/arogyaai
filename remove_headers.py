import os
import glob
import re

pages_dir = r"C:\LEARNING\TechnoMax\arogyaai\apps\frontend\src\pages"

def remove_header(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the start of the <header> block
    match = re.search(r'<header[^>]*className=[^>]*>', content)
    if not match:
        return False
        
    start_idx = match.start()
    
    # We need to find the matching </header>
    # Handle self-closing if any, though `<header>` usually has closing tag.
    if content[match.end()-2:match.end()] == '/>':
        end_idx = match.end()
    else:
        # Find the next </header> that closes this one
        header_start_count = 0
        search_idx = match.end()
        while True:
            next_open = content.find('<header', search_idx)
            next_close = content.find('</header>', search_idx)
            
            if next_close == -1:
                # Should not happen, but safeguard
                break
                
            if next_open != -1 and next_open < next_close:
                header_start_count += 1
                search_idx = next_open + 7
            else:
                if header_start_count == 0:
                    end_idx = next_close + 9
                    break
                else:
                    header_start_count -= 1
                    search_idx = next_close + 9

    if end_idx:
        new_content = content[:start_idx] + content[end_idx:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Removed header from {os.path.basename(filepath)}")
        return True
    return False

js_files = glob.glob(os.path.join(pages_dir, "*.jsx")) + glob.glob(os.path.join(pages_dir, "*.tsx"))

count = 0
for f in js_files:
    if remove_header(f):
        count += 1

print(f"Total files updated: {count}")
