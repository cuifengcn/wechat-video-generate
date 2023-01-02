import flet as ft
from pathlib import Path

MAIN_PATH = Path(__file__).absolute().parent
WORK_PATH = MAIN_PATH.joinpath("workspace")
WORK_PATH.mkdir(exist_ok=True)


def snack_bar(page, message):
    page.snack_bar = ft.SnackBar(content=ft.Text(message), action="好的")
    page.snack_bar.open = True
    page.update()
