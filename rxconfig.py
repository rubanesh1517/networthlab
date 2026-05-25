import reflex as rx

config = rx.Config(
    app_name="networthlab",
    frontend_port=8388,
    tailwind={
        "darkMode": "class",
        "theme": {
            "extend": {
                "colors": {
                    "bg": {
                        "primary": "#0f0f14",
                        "secondary": "#1a1a24",
                        "tertiary": "#252532",
                    },
                    "accent": {
                        "primary": "#8b5cf6",
                        "secondary": "#3b82f6",
                        "success": "#10b981",
                        "warning": "#f59e0b",
                        "danger": "#ef4444",
                    },
                },
                "backdropBlur": {
                    "xl": "24px",
                },
            }
        },
    },
)
