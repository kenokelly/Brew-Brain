import re
with open('app/api/automation.py', 'r') as f:
    text = f.read()

# remove routes for /api/ml/...
pattern = r"@automation_bp\.route\('/api/ml/.*?def .*?:\n(?:    .*\n)*"
text = re.sub(pattern, '', text)

with open('app/api/automation.py', 'w') as f:
    f.write(text)
