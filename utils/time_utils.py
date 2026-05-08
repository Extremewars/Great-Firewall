def format_elapsed_hhmmss(elapsed_seconds: float | int) -> str:
    """Format elapsed time as HH:MM:SS."""
    total_seconds = int(elapsed_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"
