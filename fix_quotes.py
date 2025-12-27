#!/usr/bin/env python3

with open('/app/templates/index.html', 'r') as f:
    content = f.read()

# Fix the escaped quotes
content = content.replace(r"p|time:\'H:i\'", "p|time:'H:i'")

with open('/app/templates/index.html', 'w') as f:
    f.write(content)

print('Fixed escaped quotes in template tags')
