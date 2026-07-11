# Deploying to Streamlit Cloud (Free)

## Steps
1. Go to https://share.streamlit.io — sign in with GitHub
2. Click "New app"
3. Select repo, branch: main, main file: `app/app.py`
4. Click "Deploy"

## Data Files Required in Git
data/users.csv, events.csv, sessions.csv, subscriptions.csv, ab_tests.csv, features.csv, metrics_framework.csv

If events.csv is too large for GitHub, compress it:
```bash
gzip data/events.csv
```
Then update data_loader.py line to: `pd.read_csv(..., compression="gzip")`

## After Deployment
Copy the URL → add to resume and GitHub README.
