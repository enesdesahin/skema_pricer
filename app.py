import streamlit as st

from pricer.ui.bonus_certificate_page import render_bonus_certificate_page
from pricer.ui.bonds_page import render_bonds_page
from pricer.ui.discount_certificate_page import render_discount_certificate_page
from pricer.ui.interview_page import render_interview_page
from pricer.ui.options_page import render_options_page
from pricer.ui.turbo_page import render_turbo_page


st.set_page_config(page_title="Pricer", page_icon=":bar_chart:", layout="wide")

PAGES = [
    "Options",
    "Bonds",
    "Turbo",
    "Discount Certificate",
    "Bonus Certificate",
    "Interview",
]

with st.sidebar:
    st.header("Input data")
    selected_page = st.selectbox("Data source", options=PAGES, index=0)

if selected_page == "Options":
    render_options_page()
elif selected_page == "Bonds":
    render_bonds_page()
elif selected_page == "Turbo":
    render_turbo_page()
elif selected_page == "Discount Certificate":
    render_discount_certificate_page()
elif selected_page == "Bonus Certificate":
    render_bonus_certificate_page()
elif selected_page == "Interview":
    render_interview_page()
else:
    st.error(f"Unknown page: {selected_page}")
