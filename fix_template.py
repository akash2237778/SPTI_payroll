with open('/app/templates/index.html', 'r') as f:
    lines = f.readlines()

# Remove the stray }</td> on line 145 (0-indexed: 144)
lines[144] = '\n'

# Also fix the span tag split (lines 160-161, 0-indexed: 159-160)
lines[159] = '                                    <span style="font-size: 0.7rem; background: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 4px; font-family: \'Space Grotesk\';">{{ p|time:\'H:i\' }}</span>\n'
lines[160] = ''

with open('/app/templates/index.html', 'w') as f:
    f.writelines(lines)
print('Template cleanup completed')
