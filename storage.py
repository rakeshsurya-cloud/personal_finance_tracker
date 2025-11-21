import os
import boto3
from pathlib import Path
from io import BytesIO
import pandas as pd
import streamlit as st

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

def save_file(file_name: str, data: bytes | pd.DataFrame, folder: str = "bank_data"):
    """
    Saves a file to either local disk or S3.
    """
    if S3_BUCKET:
        s3 = get_s3_client()
        key = f"{folder}/{file_name}"
        
        if isinstance(data, pd.DataFrame):
            csv_buffer = BytesIO()
            data.to_csv(csv_buffer, index=False)
            body = csv_buffer.getvalue()
        else:
            body = data
            
        try:
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
            return True
        except Exception as e:
            st.error(f"S3 Upload Error: {e}")
            return False
    else:
        # Local fallback
        local_path = Path(f"personal_finance_tracker/{folder}/{file_name}")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(data, pd.DataFrame):
            data.to_csv(local_path, index=False)
        else:
            with open(local_path, "wb") as f:
                f.write(data)
        return True

def load_file(file_name: str, folder: str = "bank_data") -> pd.DataFrame | None:
    """
    Loads a CSV file from either local disk or S3.
    """
    if S3_BUCKET:
        s3 = get_s3_client()
        key = f"{folder}/{file_name}"
        try:
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            return pd.read_csv(obj["Body"])
        except s3.exceptions.NoSuchKey:
            return None
        except Exception as e:
            st.error(f"S3 Download Error: {e}")
            return None
    else:
        # Local fallback
        local_path = Path(f"personal_finance_tracker/{folder}/{file_name}")
        if local_path.exists():
            return pd.read_csv(local_path)
        return None

def list_files(folder: str = "bank_data") -> list[str]:
    """
    Lists files in a folder (Local or S3).
    """
    if S3_BUCKET:
        s3 = get_s3_client()
        try:
            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{folder}/")
            if "Contents" in response:
                return [obj["Key"].split("/")[-1] for obj in response["Contents"]]
            return []
        except Exception:
            return []
    else:
        local_path = Path(f"personal_finance_tracker/{folder}")
        if local_path.exists():
            return [f.name for f in local_path.glob("*") if f.is_file()]
        return []
