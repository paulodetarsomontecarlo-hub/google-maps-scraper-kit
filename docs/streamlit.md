# Web app with Streamlit

`app/streamlit_app.py` is a form over the kit: type a search and a city, press **Raspar**, see the
table and download the CSV. It starts the kit's engine by itself.

## On your computer

```bash
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
```

## On Streamlit Community Cloud

1. Sign in at share.streamlit.io with GitHub and choose **Create app > Deploy a public app from GitHub**.
2. Repository: your copy of the kit. Branch: `master`. Main file path: `app/streamlit_app.py`.
3. **Advanced settings > Secrets**: add `APP_PASSWORD = "a-long-password"`. Without it anyone with the
   link can run scrapes and see the results.
4. Deploy. `packages.txt` installs Chromium; the first start takes a few minutes.

Notes: Streamlit Cloud runs on shared US data-centre IPs, so Google may rate-limit it sooner than a
home connection; keep depth modest and set the country (default `br`). The app sleeps when unused,
and results are not kept between sessions: download the CSV.
