#!/usr/bin/env python3
import re

with open('/app/templates/index.html', 'r') as f:
    content = f.read()

# Fix all split template tags by joining them
# Pattern 1: {{ tag split across lines }}
content = re.sub(
    r'{{\s+([^}]+?)\s+}}',
    r'{{ \1 }}',
    content,
    flags=re.DOTALL
)

# Pattern 2: Specifically fix the p|time:'H:i' case
content = re.sub(
    r'>\s*{{\s*p\|time:\'H:i\'\s*}}\s*<',
    r'>{{ p|time:\'H:i\' }}<',
    content
)

with open('/app/templates/index.html', 'w') as f:
    f.write(content)

print('All split template tags fixed')
