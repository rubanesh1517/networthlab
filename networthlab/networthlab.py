"""NetWorthLab - Main Reflex application."""

import reflex as rx

from networthlab.state import AppState


def stat_card(title: str, value: rx.Var) -> rx.Component:
    """Create a stat card component."""
    return rx.box(
        rx.text(title, class_name="text-sm font-medium text-gray-500"),
        rx.text(value, class_name="text-2xl font-bold text-gray-900 mt-1"),
        class_name="bg-white rounded-xl p-6 shadow-sm border border-gray-100",
    )


def connect_form() -> rx.Component:
    """API token input form."""
    return rx.box(
        rx.vstack(
            rx.heading("Connect to Lunch Money", size="6", class_name="text-gray-900"),
            rx.text(
                "Enter your API token to fetch your financial data",
                class_name="text-gray-500",
            ),
            rx.input(
                placeholder="Your Lunch Money API Token",
                type="password",
                value=AppState.api_token,
                on_change=AppState.set_api_token,
                class_name="w-full mt-4",
                size="3",
            ),
            rx.cond(
                AppState.error_message != "",
                rx.text(AppState.error_message, class_name="text-red-500 text-sm"),
                rx.fragment(),
            ),
            rx.button(
                rx.cond(
                    AppState.is_loading,
                    rx.spinner(size="1"),
                    rx.text("Connect"),
                ),
                on_click=AppState.connect_to_lunch_money,
                disabled=AppState.is_loading,
                class_name="w-full mt-4",
                size="3",
            ),
            rx.link(
                "Get your API token →",
                href="https://my.lunchmoney.app/developers",
                is_external=True,
                class_name="text-sm text-primary-600 hover:text-primary-700 mt-2",
            ),
            spacing="2",
            class_name="w-full max-w-md",
        ),
        class_name="min-h-screen flex items-center justify-center bg-gray-50 p-4",
    )


def account_item(account: dict) -> rx.Component:
    """Render a single account item."""
    return rx.hstack(
        rx.box(
            rx.text(account["name"], class_name="font-medium text-gray-900"),
            rx.text(account["type"], class_name="text-xs text-gray-500"),
        ),
        rx.spacer(),
        rx.text(
            account["balance_display"],
            class_name="font-semibold text-gray-900",
        ),
        class_name="w-full py-3 border-b border-gray-100 last:border-0",
    )


def dashboard() -> rx.Component:
    """Main dashboard view."""
    return rx.box(
        # Header
        rx.box(
            rx.hstack(
                rx.heading("NetWorthLab", size="6", class_name="text-gray-900 font-bold"),
                rx.spacer(),
                rx.button(
                    "Refresh",
                    on_click=AppState.connect_to_lunch_money,
                    variant="outline",
                    size="2",
                ),
                class_name="w-full",
            ),
            class_name="bg-white border-b border-gray-200 px-6 py-4",
        ),
        # Content
        rx.box(
            # Stats row
            rx.box(
                rx.hstack(
                    stat_card("Net Worth", AppState.net_worth_display),
                    stat_card("Investments", AppState.investments_display),
                    stat_card("Monthly Savings", AppState.monthly_savings_display),
                    stat_card("FIRE Year", AppState.fire_year_display),
                    spacing="4",
                    class_name="w-full flex-wrap",
                ),
                class_name="mb-8",
            ),
            # FIRE Progress
            rx.cond(
                AppState.has_fire_result,
                rx.box(
                    rx.text("FIRE Progress", class_name="text-lg font-semibold text-gray-900 mb-4"),
                    rx.box(
                        rx.box(
                            class_name="h-4 bg-green-500 rounded-full transition-all",
                            style={"width": AppState.fire_progress_percent.to_string() + "%"},
                        ),
                        class_name="w-full h-4 bg-gray-200 rounded-full overflow-hidden",
                    ),
                    rx.hstack(
                        rx.text(
                            AppState.fire_progress_display + " complete",
                            class_name="text-sm text-gray-500",
                        ),
                        rx.spacer(),
                        rx.text(
                            "Target: " + AppState.fire_number_display,
                            class_name="text-sm text-gray-500",
                        ),
                        class_name="w-full mt-2",
                    ),
                    class_name="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8",
                ),
                rx.fragment(),
            ),
            # Settings sliders
            rx.box(
                rx.text("Projection Settings", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            AppState.expected_return_display,
                            class_name="text-sm text-gray-600 w-48",
                        ),
                        rx.slider(
                            default_value=[7],
                            min=1,
                            max=15,
                            step=0.5,
                            on_value_commit=AppState.update_expected_return,
                            class_name="flex-1",
                        ),
                        class_name="w-full",
                    ),
                    rx.hstack(
                        rx.text(
                            AppState.withdrawal_rate_display,
                            class_name="text-sm text-gray-600 w-48",
                        ),
                        rx.slider(
                            default_value=[4],
                            min=2,
                            max=6,
                            step=0.25,
                            on_value_commit=AppState.update_withdrawal_rate,
                            class_name="flex-1",
                        ),
                        class_name="w-full",
                    ),
                    rx.hstack(
                        rx.text(
                            AppState.inflation_rate_display,
                            class_name="text-sm text-gray-600 w-48",
                        ),
                        rx.slider(
                            default_value=[3],
                            min=1,
                            max=6,
                            step=0.25,
                            on_value_commit=AppState.update_inflation_rate,
                            class_name="flex-1",
                        ),
                        class_name="w-full",
                    ),
                    spacing="4",
                    class_name="w-full",
                ),
                class_name="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8",
            ),
            # Accounts list
            rx.box(
                rx.text("Accounts", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.foreach(AppState.accounts, account_item),
                class_name="bg-white rounded-xl p-6 shadow-sm border border-gray-100",
            ),
            class_name="p-6 max-w-6xl mx-auto",
        ),
        class_name="min-h-screen bg-gray-50",
    )


def index() -> rx.Component:
    """Main page - show connect form or dashboard."""
    return rx.cond(
        AppState.is_connected,
        dashboard(),
        connect_form(),
    )


# Create app
app = rx.App(
    theme=rx.theme(
        accent_color="green",
        radius="large",
    ),
)
app.add_page(index, title="NetWorthLab")
