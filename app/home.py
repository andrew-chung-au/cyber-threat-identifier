#!/usr/bin/env python3
"""Cyber Threat Identifier — Home Page."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

APP_TITLE = "cyber-threat-identifier"


def render_sidebar() -> None:
    """Render sidebar with concise about and system information."""
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This tool maps incident narratives to likely MITRE ATT&CK techniques.

        **How it works**
        1. Enter an incident narrative
        2. System retrieves relevant ATT&CK techniques
        3. LLM generates a grounded, structured answer

        **Feedback**
        Use the thumbs up/down buttons to help improve the system.
        """)

        st.divider()
        st.markdown("**System info**")
        st.caption("📚 1,200+ ATT&CK techniques")
        st.caption(f"🤖 {os.getenv('MODEL_ID', 'Model selection pending DEC-021')}")
        st.caption("🔧 Retrieval: Vector + cross-encoder reranking")


def render_home_tab() -> None:
    """Render the Home tab."""
    st.header("🔍 Cyber Threat Identifier")
    st.markdown("""
    ### Map incident narratives to MITRE ATT&CK techniques

    This tool helps security analysts map incident narratives to likely MITRE ATT&CK techniques using retrieval-augmented generation.

    ### What you can do
    - Paste an incident narrative and get suggested ATT&CK techniques
    - Inspect which techniques were retrieved and why
    - Provide feedback on the usefulness of answers

    ### Data sources
    - Incident narratives: [Security-TTP-Mapping](https://github.com/tumeteor/mitre-ttp-mapping) dataset by [tumeteor](https://github.com/tumeteor/mitre-ttp-mapping), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
    - ATT&CK techniques: [MITRE ATT&CK](https://attack.mitre.org/) knowledge base.

    ### ATT&CK usage
    MITRE ATT&CK is a registered trademark of The MITRE Corporation.
    This tool uses ATT&CK under the [Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use).
    © 2026 The MITRE Corporation. Used with permission.
    """)


def render_query_tab() -> None:
    st.header("🔍 Query Interface")
    try:
        from app.query import render_query_interface
        render_query_interface()
    except Exception as error:
        st.warning(f"Query interface not available: {error}")


def render_dashboard_tab() -> None:
    st.header("📊 Monitoring Dashboard")
    try:
        from app.dashboard import render_monitoring_dashboard
        render_monitoring_dashboard()
    except Exception as error:
        st.warning(f"Dashboard not available: {error}")


def render_evaluation_tab() -> None:
    st.header("🧪 Evaluation Review")
    try:
        from app.evaluation import render_evaluation_review
        render_evaluation_review()
    except Exception as error:
        st.warning(f"Evaluation review not available: {error}")


def main() -> None:
    """Main entry point."""
    st.set_page_config(page_title=APP_TITLE, page_icon="🔍", layout="wide")
    render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🏠 Home", "🔍 Query", "📊 Dashboard", "🧪 Evaluation Review"]
    )
    with tab1:
        render_home_tab()
    with tab2:
        render_query_tab()
    with tab3:
        render_dashboard_tab()
    with tab4:
        render_evaluation_tab()


if __name__ == "__main__":
    main()