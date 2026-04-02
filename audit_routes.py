import re
import os

def audit_routes():
    base_dir = r"c:\LEARNING\TechnoMax\arogyaai\apps\frontend\src"
    routes_file = os.path.join(base_dir, "router", "routes.js")
    router_file = os.path.join(base_dir, "router", "index.jsx")
    nav_file = os.path.join(base_dir, "config", "navConfig.ts")

    # 1. Parse routes.js
    with open(routes_file, 'r') as f:
        routes_content = f.read()
    
    routes_map = {}
    # Find patterns like NAME: 'value'
    matches = re.finditer(r"([A-Z0-9_]+):\s+['\"]([^'\"]+)['\"]", routes_content)
    for m in matches:
        routes_map[m.group(1)] = m.group(2)

    # 2. Parse navConfig.ts
    with open(nav_file, 'r') as f:
        nav_content = f.read()
    
    # We want paths used in navConfig
    # Look for path: ROUTES.NAME
    nav_paths = []
    matches = re.finditer(r"path:\s+ROUTES\.([A-Z0-9_]+)", nav_content)
    for m in matches:
        name = m.group(1)
        if name in routes_map:
            nav_paths.append(routes_map[name])
        else:
            print(f"ERROR: navConfig uses unknown ROUTES.{name}")

    # 3. Parse router/index.jsx
    with open(router_file, 'r') as f:
        router_content = f.read()

    # Find registered paths
    # Look for path={ROUTES.NAME} or path={`${ROUTES.NAME}/*`}
    registered_routes = []
    # Match path={ROUTES.NAME}
    matches = re.finditer(r"path=\{ROUTES\.([A-Z0-9_]+)\}", router_content)
    for m in matches:
        name = m.group(1)
        if name in routes_map:
            registered_routes.append(routes_map[name])
    
    # Match path={`${ROUTES.NAME}/*`}
    matches = re.finditer(r"path=\{\`\$\{ROUTES\.([A-Z0-9_]+)\}\/\*`\}", router_content)
    for m in matches:
        name = m.group(1)
        if name in routes_map:
            registered_routes.append(routes_map[name])

    print("\n=== ROUTE AUDIT ===\n")
    print(f"Total Sidebar Paths: {len(nav_paths)}")
    print(f"Total Registered Paths in Router: {len(registered_routes)}")

    missing = []
    for path in nav_paths:
        if path not in registered_routes:
            missing.append(path)
    
    if not missing:
        print("SUCCESS: All Sidebar paths are registered in the Router.")
    else:
        print("FAILURE: The following Sidebar paths are NOT found in the Router index.jsx:")
        for m in sorted(list(set(missing))):
            print(f" - {m}")

audit_routes()
