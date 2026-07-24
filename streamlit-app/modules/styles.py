"""
Snowflake Streamlit Design System — AI Spend Tracker edition.
Drop-in module. Call apply_styles() immediately after st.set_page_config().
"""

import streamlit as st

SNOWFLAKE_LOGO = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/"
    "Snowflake_Logo.svg/1280px-Snowflake_Logo.svg.png"
)

MAIN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        padding: 12px;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 8px;
        color: #334155;
        font-weight: 500;
        padding: 10px 24px;
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f8fafc;
        border-color: #29B5E8;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #29B5E8 0%, #0ea5e9 100%) !important;
        color: white !important;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(41, 181, 232, 0.3);
    }

    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 0.8rem 1rem;
        border-radius: 10px;
        border-left: 4px solid #29B5E8;
        margin: 0.3rem 0;
    }
    .metric-card h3 { margin: 0 0 2px 0; font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-card .value { font-size: 1.4rem; font-weight: 700; color: #1e293b; margin: 0; line-height: 1.2; }
    .metric-card .subvalue { font-size: 0.75rem; color: #64748b; margin-top: 2px; }

    .metric-card-green { border-left-color: #10b981; }
    .metric-card-orange { border-left-color: #f97316; }
    .metric-card-purple { border-left-color: #8b5cf6; }
</style>
"""

COMPONENT_CSS = """
<style>
    :root {
        --sf-blue: #29B5E8;
        --sf-blue-dark: #0ea5e9;
        --text-primary: #1e293b;
        --text-secondary: #334155;
        --text-muted: #64748b;
        --border-light: #e2e8f0;
        --bg-subtle: #f8fafc;
        --color-success: #10b981;
        --color-success-dk: #059669;
        --color-success-bg: #d1fae5;
        --color-warning: #f59e0b;
        --color-warning-dk: #d97706;
        --color-warning-bg: #fff3cd;
        --color-error: #ef4444;
        --color-error-dk: #dc3545;
        --color-error-bg: #fee2e2;
        --color-info: #3b82f6;
        --color-info-dk: #2196f3;
        --color-info-bg: #e3f2fd;
        --color-orange: #f97316;
        --color-orange-dk: #c2410c;
        --color-orange-bg: #fff7ed;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-pill: 20px;
    }

    .alert-card {
        padding: 12px 16px;
        border-radius: var(--radius-md);
        margin-bottom: 10px;
        border-left: 4px solid currentColor;
    }
    .alert-info    { background: var(--color-info-bg);    color: var(--color-info-dk); }
    .alert-success { background: var(--color-success-bg); color: var(--color-success-dk); }
    .alert-warning { background: var(--color-warning-bg); color: var(--color-warning-dk); }
    .alert-error   { background: var(--color-error-bg);   color: var(--color-error-dk); }
    .alert-card p, .alert-card span { color: var(--text-primary); }

    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: var(--radius-pill);
        font-size: 12px;
        font-weight: 600;
        color: white;
    }
    .badge-success { background: linear-gradient(135deg, var(--color-success), var(--color-success-dk)); }
    .badge-warning { background: linear-gradient(135deg, var(--color-warning), var(--color-warning-dk)); }
    .badge-info    { background: linear-gradient(135deg, var(--color-info), var(--color-info-dk)); }
    .badge-error   { background: linear-gradient(135deg, var(--color-error), var(--color-error-dk)); }

    .cta-banner {
        border-radius: var(--radius-lg);
        padding: 20px 24px;
        margin: 16px 0;
    }
    .cta-banner p { margin: 0; line-height: 1.2; }
    .cta-banner-blue {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 2px solid var(--color-info);
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.15);
    }
    .cta-banner-blue p { font-size: 1.1rem; font-weight: 500; color: #1e40af; }
    .cta-banner-orange {
        background: linear-gradient(135deg, var(--color-orange-bg) 0%, #ffedd5 100%);
        border: 2px solid var(--color-orange);
        box-shadow: 0 4px 6px -1px rgba(249, 115, 22, 0.15);
    }
    .cta-banner-orange p { font-size: 1.1rem; font-weight: 600; color: var(--color-orange-dk); }

    .insight-item {
        background: var(--bg-subtle);
        padding: 12px 16px;
        border-radius: var(--radius-md);
        margin-bottom: 10px;
        font-size: 0.9em;
        border: 1px solid var(--border-light);
        border-left: 3px solid var(--sf-blue);
    }

    .section-header {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-muted);
        margin: 24px 0 8px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--border-light);
    }
</style>
"""


def apply_styles() -> None:
    st.markdown(MAIN_CSS, unsafe_allow_html=True)
    st.markdown(COMPONENT_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, subvalue: str = "", color: str = "") -> str:
    cls = f"metric-card metric-card-{color}" if color else "metric-card"
    sub = f'<p class="subvalue">{subvalue}</p>' if subvalue else ""
    return f'<div class="{cls}"><h3>{label}</h3><p class="value">{value}</p>{sub}</div>'


def alert_card(text: str, kind: str = "info") -> str:
    kind = kind if kind in ("info", "success", "warning", "error") else "info"
    return f'<div class="alert-card alert-{kind}"><p>{text}</p></div>'


def badge(text: str, kind: str = "success") -> str:
    kind = kind if kind in ("success", "warning", "info", "error") else "info"
    return f'<span class="badge badge-{kind}">{text}</span>'


def cta_banner(text: str, kind: str = "blue") -> str:
    kind = kind if kind in ("orange", "blue") else "blue"
    return f'<div class="cta-banner cta-banner-{kind}"><p>{text}</p></div>'


def insight_item(text: str) -> str:
    return f'<div class="insight-item">{text}</div>'


def section_header(text: str) -> str:
    return f'<div class="section-header">{text}</div>'
