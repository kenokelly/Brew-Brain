import re
with open('app/api/routes.py', 'r') as f:
    text = f.read()

# The routes to remove are:
# @api_bp.route('/ml/predict')
# def predict_active_batch():
# ...
# @api_bp.route('/ml/peers')
# ...
# @api_bp.route('/ml/models')
# ...
# @api_bp.route('/ml/train', methods=['POST'])
# @require_api_token
# def train_ml_models():
# ...

pattern = r"@api_bp\.route\('/ml/predict'\).*?(?=@api_bp\.route|\Z)"
text = re.sub(pattern, '', text, flags=re.DOTALL)

pattern2 = r"@api_bp\.route\('/ml/peers'\).*?(?=@api_bp\.route|\Z)"
text = re.sub(pattern2, '', text, flags=re.DOTALL)

pattern3 = r"@api_bp\.route\('/ml/models'\).*?(?=@api_bp\.route|\Z)"
text = re.sub(pattern3, '', text, flags=re.DOTALL)

pattern4 = r"@api_bp\.route\('/ml/train'.*?(?=@api_bp\.route|\Z)"
text = re.sub(pattern4, '', text, flags=re.DOTALL)

with open('app/api/routes.py', 'w') as f:
    f.write(text)
