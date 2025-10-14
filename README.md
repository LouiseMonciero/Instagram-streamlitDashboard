# Instagram-streamlitDashboard
Understand what Meta knows about you. This streamlit dashboard helps visualize your instagram personal data with minimal machine learning and dynamic figures.

## Use your own personnal data :
1. Downloads as JSON your personnal data from your own instagram acocunt : https://accountscenter.instagram.com/info_and_permissions/dyi/?theme=dark

2. Unzip the file and put it inside app/data

3. Create your .env files inside 'app/'
```.env
DATA_PATH = './data/name_of_your_folder'
```

## Run the app
Inside './app/'
```bash
streamlit run app.py
```