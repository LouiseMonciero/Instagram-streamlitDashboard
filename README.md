# Instagram-streamlitDashboard
Understand what Meta knows about you. This streamlit dashboard helps visualize your instagram personal data with minimal machine learning and dynamic figures.

## Use your own personnal data :
1. Downloads as JSON your personnal data from your own instagram acocunt : https://accountscenter.instagram.com/info_and_permissions/dyi/?theme=dark

2. Unzip the file and put it inside app/data

3. Create your .env files inside 'app/'

```.env
DATA_PATH = './data/name_of_your_folder'
HEADERS = {
    # add a real contact if you can (policy requirement)
    "User-Agent": "Lou-CompanyEnricher/0.1 (contact: you@example.com)"
}
```

## Installation complète
1. Install your python environement
E.g.
```bash
pyenv install 3.11.9
```

2. Create and activate the virtual environement

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

5. Run the dashboard in 'app/' :

```bash
streamlit run app.py
```