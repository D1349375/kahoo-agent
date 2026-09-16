"""
Rich CLI Dashboard and Commands for kahoo-agent.
"""

import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from .config import Settings, get_settings
from .models import AnswerResult, Option, Question, STANDARD_OPTIONS_MAP
from .solvers.cdp_solver import CDPSolver
from .solvers.vision_solver import VisionSolver
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)

COLOR_STYLES = {
    "red": "bold white on red",
    "blue": "bold white on blue",
    "yellow": "bold black on yellow",
    "green": "bold white on green",
}


def print_banner():
    banner_text = """[bold cyan]
   ███████╗ █████╗ ██╗  ██╗ ██████╗  ██████╗ 
   ██╔════╝██╔══██╗██║  ██║██╔═══██╗██╔═══██╗
   ███████╗███████║███████║██║   ██║██║   ██║
   ╚════██║██╔══██║██╔══██║██║   ██║██║   ██║
   ███████║██║  ██║██║  ██║╚██████╔╝╚██████╔╝
   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ 
             [magenta]Kahoot AI Agent v0.1.0[/magenta]
    """
    console.print(Panel(banner_text, subtitle="[dim]Powered by Google Gemini & Playwright[/dim]"))


def render_question(q: Question):
    table = Table(title=f"[bold yellow]🎯 Question Detected: {q.text}[/bold yellow]", show_header=True)
    table.add_column("Idx", style="dim", width=4)
    table.add_column("Color / Shape", width=18)
    table.add_column("Option Text")

    for opt in q.options:
        style = COLOR_STYLES.get(opt.color.value, "white")
        badge = f"[{style}] {opt.color.value.upper()} {opt.shape.value} [/{style}]"
        table.add_row(str(opt.index), badge, opt.text or "(Hidden on player device)")

    console.print(table)


def render_answer(result: AnswerResult):
    dec = result.decision
    indices_str = ", ".join(str(idx) for idx in dec.selected_indices)

    colors = []
    for idx in dec.selected_indices:
        opt = Option.from_index(idx)
        style = COLOR_STYLES.get(opt.color.value, "white")
        colors.append(f"[{style}] {opt.color.value.upper()} ({opt.shape.value}) [/{style}]")

    console.print(
        Panel(
            f"[bold green]Selected Choice:[/] {indices_str} -> {' '.join(colors)}\n"
            f"[bold cyan]Confidence:[/] {dec.confidence * 100:.1f}%\n"
            f"[bold cyan]Latency:[/] [bold magenta]{result.latency_ms:.1f} ms[/bold magenta]\n"
            f"[bold cyan]Reasoning:[/] {dec.reasoning or 'Direct prediction'}",
            title="[bold green]⚡ AI Answer Computed[/bold green]",
            border_style="green",
        )
    )


@click.group()
def cli():
    """kahoo-agent: High-performance AI Kahoot assistant."""
    pass


@cli.command()
@click.option("--port", default=9222, help="Chrome remote debugging port.")
@click.option("--delay", default=0.4, type=float, help="Delay before clicking in seconds.")
@click.option("--mode", type=click.Choice(["auto", "assist"]), default="auto", help="Auto click or assist mode.")
def cdp(port: int, delay: float, mode: str):
    """Run in CDP browser takeover mode (recommended)."""
    print_banner()
    settings = get_settings()
    settings.browser.cdp_url = f"http://localhost:{port}"
    settings.gameplay.answer_delay_sec = delay
    settings.gameplay.mode = mode

    console.print(f"[bold cyan]Starting CDP Solver connecting to port {port}...[/bold cyan]")
    console.print("[dim]Make sure Chrome was launched with --remote-debugging-port=9222 and you are in the game.[/dim]\n")

    solver = CDPSolver(
        settings=settings,
        on_question_detected=render_question,
        on_answer_calculated=render_answer,
        on_status_update=lambda msg: console.print(f"[dim]LOG:[/] {msg}"),
    )
    solver.start()


@cli.command()
@click.option("--roi", default=None, help="Comma-separated ROI: top,left,width,height")
@click.option("--delay", default=0.4, type=float, help="Delay before clicking in seconds.")
def vision(roi: str, delay: float):
    """Run in multimodal screen vision mode (for projector/Zoom host screen)."""
    print_banner()
    settings = get_settings()
    settings.gameplay.answer_delay_sec = delay
    if roi:
        try:
            settings.vision.roi = [int(x.strip()) for x in roi.split(",")]
        except Exception:
            console.print("[bold red]Invalid ROI format. Use: top,left,width,height[/bold red]")
            sys.exit(1)

    console.print("[bold cyan]Starting Vision Solver watching host screen...[/bold cyan]")
    solver = VisionSolver(
        settings=settings,
        on_answer_calculated=render_answer,
        on_status_update=lambda msg: console.print(f"[dim]LOG:[/] {msg}"),
    )
    solver.start()


@cli.command(name="test-ai")
def test_ai():
    """Quick diagnostic test of the AI reasoning engine."""
    print_banner()
    settings = get_settings()
    from .ai.engine import get_ai_engine

    console.print("[yellow]Testing AI Reasoning Engine with a sample trivia question...[/yellow]")
    engine = get_ai_engine(settings.ai)

    sample_q = Question(
        text="What is the chemical symbol for Gold?",
        options=[
            Option.from_index(0, "Ag"),
            Option.from_index(1, "Au"),
            Option.from_index(2, "Fe"),
            Option.from_index(3, "Pb"),
        ],
    )
    render_question(sample_q)
    res = engine.solve_question(sample_q)
    render_answer(res)
    console.print("\n[bold green]✓ Diagnostic complete![/bold green]")
