import shutil
from datetime import datetime
from pathlib import Path
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
src = Path("database/app.db")
dst = Path(f"database/app.db.backup_{timestamp}")
shutil.copy2(src, dst)
print(f"Backup created: {dst}")
