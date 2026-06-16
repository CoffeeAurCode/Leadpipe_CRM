from dotenv import load_dotenv
import os

load_dotenv()
print("KEY:", os.environ.get("SENDGRID_API_KEY"))
print("LEN:", len(os.environ.get("SENDGRID_API_KEY") or ""))
