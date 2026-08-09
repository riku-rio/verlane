import typer

from verlane import __version__

app = typer.Typer(add_completion=False, invoke_without_command=True)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show the Verlane version and exit.",
    ),
) -> None:
    typer.echo("Not Implemented Yet")
