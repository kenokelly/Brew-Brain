import re
import os

# 1. Fix app/api/batches.py
with open('app/api/batches.py', 'r') as f:
    text = f.read()

# remove garbage at the end
text = re.sub(r'r"\)\s*\)\s*r"\)\s*$', '', text)
text = text.replace('from app.core', 'from core')
text = text.replace('from app.api', 'from api')
text = text.replace('from app.services', 'from services')
text = text.replace("from typing import Tuple, Response", "from typing import Tuple\nfrom flask import Response")
text = text.replace("@batches_bp.route('/api/", "@batches_bp.route('/")

with open('app/api/batches.py', 'w') as f:
    f.write(text)

# 2. Fix app/api/settings.py
with open('app/api/settings.py', 'r') as f:
    text = f.read()

text = text.replace('from app.core', 'from core')
text = text.replace('from app.api', 'from api')
text = text.replace('from app.models', 'from models')
text = text.replace("from typing import Tuple, Response", "from typing import Tuple\nfrom flask import Response")
text = text.replace("@settings_bp.route('/api/", "@settings_bp.route('/")

with open('app/api/settings.py', 'w') as f:
    f.write(text)

# 3. Fix app/api/taps.py
with open('app/api/taps.py', 'r') as f:
    text = f.read()

text = text.replace('from app.core', 'from core')
text = text.replace('from app.api', 'from api')
text = text.replace("from typing import Tuple, Response", "from typing import Tuple\nfrom flask import Response")
text = text.replace("@taps_bp.route('/api/", "@taps_bp.route('/")

with open('app/api/taps.py', 'w') as f:
    f.write(text)

# 4. Fix app/api/ml.py
with open('app/api/ml.py', 'r') as f:
    text = f.read()

text = text.replace('from app.core', 'from core')
text = text.replace('from app.api', 'from api')
text = text.replace("from typing import Tuple, Response", "from typing import Tuple\nfrom flask import Response")

with open('app/api/ml.py', 'w') as f:
    f.write(text)

