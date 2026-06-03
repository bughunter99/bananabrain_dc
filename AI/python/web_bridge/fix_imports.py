#!/usr/bin/env python
"""Fix __future__ imports in Python files."""

import os

files_to_fix = [
    'd:\\data3\\bwapid_ai_dc\\AI\\python\\web_bridge\\cppsource\\OpponentModel.py',
    'd:\\data3\\bwapid_ai_dc\\AI\\python\\web_bridge\\cppsource\\PathFinder.py',
    'd:\\data3\\bwapid_ai_dc\\AI\\python\\web_bridge\\cppsource\\Results.py',
    'd:\\data3\\bwapid_ai_dc\\AI\\python\\web_bridge\\cppsource\\Strategy.py',
    'd:\\data3\\bwapid_ai_dc\\AI\\python\\web_bridge\\cppsource\\Tactics.py',
]

for fname in files_to_fix:
    if not os.path.exists(fname):
        print(f"❌ File not found: {fname}")
        continue
    
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find __future__ imports at wrong positions and remove them
        fixed_lines = []
        for i, line in enumerate(lines):
            if 'from __future__ import' in line:
                # Only keep if it's in the first few lines (before any other imports or code)
                if i > 3 or any(l.strip() and not l.strip().startswith('#') and not l.strip().startswith('"""') for l in lines[:i]):
                    continue  # Skip this line
            fixed_lines.append(line)
        
        with open(fname, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print(f"✅ Fixed {os.path.basename(fname)}")
    except Exception as e:
        print(f"❌ Error fixing {fname}: {e}")

print("\n✅ All files processed")
