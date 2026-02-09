# Instagram-streamlitDashboard
Understand what Meta knows about you. This streamlit dashboard helps visualize your instagram personal data with minimal machine learning and dynamic figures.

## Demo 
The Dashboard allows you to visualize many data depending on your profile. Here are some sight of the app :
| | |
|---|---|
| ![Demo Screenshot 1](/demo/Upload_data.png) | ![Demo Screenshot 2](/demo/Home_page.png) |
| ![Demo Screenshot 3](/demo/Galery_eg.png) | ![Demo Screenshot 4](/demo/Activities_eg.png) |

## Use your own personnal data :
This dashboard allows you to see your personal Instagram information, it won't be effective without any data giiven and will ask you to upload your personal data. You can upload manually the data with the following steps :

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

## Quick Setup
0. Clone the git repository
```bash
git clone [...]
```

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
