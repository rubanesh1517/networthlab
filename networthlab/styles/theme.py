"""Design system theme configuration."""

# Color Palette
COLORS = {
    "bg_primary": "#0f0f14",
    "bg_secondary": "#1a1a24",
    "bg_tertiary": "#252532",
    "accent_primary": "#8b5cf6",
    "accent_secondary": "#3b82f6",
    "accent_success": "#10b981",
    "accent_warning": "#f59e0b",
    "accent_danger": "#ef4444",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "glass_bg": "rgba(26,26,36,0.7)",
    "glass_border": "rgba(255,255,255,0.1)",
}

# Gradient definitions
GRADIENTS = {
    "primary": "linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)",
    "success": "linear-gradient(135deg, #10b981 0%, #3b82f6 100%)",
    "fire": "linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)",
    "purple_blue": "linear-gradient(135deg, #8b5cf6 0%, #3b82f6 50%, #10b981 100%)",
}

# Glass card effect styles
GLASS_CARD = {
    "background": COLORS["glass_bg"],
    "backdrop_filter": "blur(24px)",
    "border": f"1px solid {COLORS['glass_border']}",
    "border_radius": "16px",
}

# Chart color schemes
CHART_COLORS = [
    "#8b5cf6",  # Purple
    "#3b82f6",  # Blue
    "#10b981",  # Green
    "#f59e0b",  # Amber
    "#ef4444",  # Red
    "#ec4899",  # Pink
    "#06b6d4",  # Cyan
]

# Common style utilities
def glass_card_style(padding: str = "6") -> dict:
    """Return glassmorphism card style."""
    return {
        "background": COLORS["glass_bg"],
        "backdrop_filter": "blur(24px)",
        "border": f"1px solid {COLORS['glass_border']}",
        "border_radius": "16px",
        "padding": f"{padding}",
    }


def gradient_text_style(gradient: str = "primary") -> dict:
    """Return gradient text style."""
    return {
        "background": GRADIENTS.get(gradient, GRADIENTS["primary"]),
        "background_clip": "text",
        "-webkit-background-clip": "text",
        "color": "transparent",
    }
