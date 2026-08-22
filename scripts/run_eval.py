import sys
from pathlib import Path

# Add repo root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from tests.eval.run_eval import main  # noqa: E402

if __name__ == "__main__":
    main()
