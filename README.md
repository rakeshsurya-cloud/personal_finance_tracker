# Personal Finance Tracker

This repository contains a small, private personal finance tracking
system written in Python.  It reads exported bank and credit card
statements, categorizes each transaction using a simple natural
language classifier, aggregates the results and generates an
interactive dashboard.

## Motivation

Modern personal finance apps often rely on cloud services and closed
platforms.  To maintain privacy and control, this project shows how
you can build your own tracker that runs locally on your own
computer.  The core ideas align with the goals described in the
research and commentary on local AI models and zero‑shot
classification【440481009769778†L21-L48】【516236976776690†L123-L156】.  While sophisticated large language
models exist for categorising text【512379353540472†L53-L116】, many of them require
heavy dependencies.  To avoid those constraints, this project uses a
lightweight scikit‑learn pipeline trained on a curated set of
transaction descriptions.  You can extend the training data or
replace the classifier with a more capable local model (e.g. via
Ollama or HuggingFace) once your environment supports it【440481009769778†L27-L49】.

## Project Structure

- **`training_data.py`** – defines a list of example transaction
  descriptions and categories used for initial model training.  Feel
  free to extend or replace this list with your own labelled data.
- **`train_classifier.py`** – trains a `TfidfVectorizer` + logistic
  regression model on the training data.  You can pass a CSV with
  custom labels via `--data`.  The model is saved to
  `personal_finance_tracker/models/transaction_classifier.pkl`.
- **`process_transactions.py`** – scans a directory of exported
  statements, infers the relevant columns (date, description, amount),
  classifies each row, writes a combined CSV and generates an
  interactive dashboard.
- **`dashboard.py`** – helper functions for building a Plotly HTML
  dashboard summarising spending by category and cash flow over
  time.
- **`bank_data/`** – this folder is **not** included in the
  repository.  Create it and drop your exported statements here.  The
  script supports CSV, XLS and XLSX formats.  You can export
  statements from your bank’s website as CSV/Excel files【440481009769778†L27-L49】.
- **`models/`** – stores the trained classifier.
- **`output/`** – holds the generated `categorized_transactions.csv`
  and `dashboard.html`.

## Prerequisites

Python 3.11 is available in this environment.  The following
dependencies are already installed:

* [pandas](https://pandas.pydata.org/) for data manipulation
* [scikit‑learn](https://scikit-learn.org/) for the classifier
* [plotly](https://plotly.com/python/) for interactive charts

If you wish to train or run the scripts on your own machine, install
these packages with pip:

```bash
pip install pandas scikit-learn plotly
```

## Training the Classifier

To train the classifier on the default examples:

```bash
python train_classifier.py
```

To use your own labelled data, create a CSV with two columns
(`Description` and `Category`) and pass it via `--data`:

```bash
python train_classifier.py --data my_training_data.csv --model-output my_model.pkl
```

The script serialises the vectorizer and model using pickle.

## Processing Statements

1. Export your bank and credit card statements in CSV or Excel format
   and place them in the `bank_data/` folder.
2. Train the classifier if you haven’t already.
3. Run the processing script:

   ```bash
   python process_transactions.py \
       --input-dir personal_finance_tracker/bank_data \
       --model personal_finance_tracker/models/transaction_classifier.pkl \
       --output-csv personal_finance_tracker/output/categorized_transactions.csv \
       --dashboard personal_finance_tracker/output/dashboard.html
   ```

   The script reads all statement files, infers column names,
   classifies transactions, writes a combined CSV and generates a
   dashboard.

4. Open `output/dashboard.html` in your browser.  Because the HTML
   includes Plotly via its CDN, you can view it offline.  Transfer it
   to your phone via AirDrop, a USB cable or sync it through a cloud
   folder.

## Extending the System

* **Improving the classifier** – Add more labelled examples to
  `training_data.py` or supply your own CSV.  The classifier uses
  unigrams and bigrams; additional examples will help it generalise.
* **Local LLMs** – If you have hardware that supports local
  inference, you can replace the scikit‑learn classifier with an
  open‑source model loaded through [Ollama](https://ollama.com/) or
  [Hugging Face](https://huggingface.co/)【440481009769778†L27-L49】.  The training script
  here is modular, so you can substitute your own categorization
  function in `process_transactions.py`.
* **Automation** – Schedule the processing script to run regularly
  using cron (Linux/macOS) or Task Scheduler (Windows) so your
  dashboard stays up to date.  Because the script reads all files
  every time, it will ignore duplicates and aggregate new data
  automatically.
* **Smart Insights** – The Streamlit app now layers AI-like behaviors
  on top of your processed data (auto-categorization, budgets,
  anomaly detection, cash-flow projections, predictive nudges, and an
  on-page assistant). See `docs/SMART_INSIGHTS.md` for how these
  features are computed.

## Privacy Considerations

All processing happens locally on your machine.  The sample training
data does **not** contain any personal information.  When you export
your own statements, avoid uploading them to cloud services unless you
trust the provider.  If you prefer absolute control, keep the
repository and processed files on an encrypted disk or use a
cryptographic filesystem.  The zero‑shot classification research
emphasises that modern models can generalise to unseen categories
without requiring labelled data【516236976776690†L123-L156】, but running a local model like
CatBoost or an offline LLM ensures your spending data never leaves
your machine【440481009769778†L27-L49】.
