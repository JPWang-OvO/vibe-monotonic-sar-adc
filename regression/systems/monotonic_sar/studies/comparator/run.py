"""Run the comparator study."""
from pathlib import Path
from regression.common.runner import main


if __name__ == '__main__':
    main(Path(__file__).with_name('study.json'))
