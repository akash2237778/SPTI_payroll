#!/usr/bin/env python3
import re

with open('/app/templates/index.html', 'r') as f:
    content = f.read()

# Fix the split template tags by joining them
content = re.sub(
    r'{{\s*summary\.first_check_in\|time:\'H:i\'\|default:\'-\'\s*}}',
    '{{ summary.first_check_in|time:\'H:i\'|default:\'-\' }}',
    content
)

content = re.sub(
    r'{{\s*summary\.last_check_out\|time:\'H:i\'\|default:\'-\'\s*}}',
    '{{ summary.last_check_out|time:\'H:i\'|default:\'-\' }}',
    content
)

with open('/app/templates/index.html', 'w') as f:
    f.write(content)

print('Template tags fixed and joined')
