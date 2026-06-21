"""`python -m ads1292_studio` launches the PySide6 (Qt) app.

The legacy Tk app remains available via `python -m ads1292_studio.app` or the
`ads1292-studio-tk` console script.
"""
from ads1292_studio.app_qt import main


if __name__ == "__main__":
    main()
