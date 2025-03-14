import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF  # pip install fpdf2
from PIL import Image  # for image handling

# ---------------------- PAGE CONFIGURATION & STARTUP VIDEO ---------------------- #
st.set_page_config(page_title="OS4P Green Sentinel", layout="wide")

if "video_viewed" not in st.session_state:
    st.session_state["video_viewed"] = False

if not st.session_state["video_viewed"]:
    st.video("OS4P.mp4")
    if st.button("Continue to the Application"):
        st.session_state["video_viewed"] = True
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.warning("Your version of Streamlit does not support automatic rerun. Please refresh the page manually.")
else:
    # ---------------------- CORE CALCULATION FUNCTIONS ---------------------- #
    def calculate_innovation_fund_score(cost_efficiency_ratio):
        """
        Calculate Innovation Fund score based on cost efficiency ratio.
        For INNOVFUND-2024-NZT-PILOTS topic:
          - If cost efficiency ratio is <= 2000 EUR/t CO₂-eq, score = 12 - (12 × (ratio / 2000))
          - Otherwise: score = 0
        Returns the score rounded to the nearest half‐point.
        """
        if cost_efficiency_ratio <= 2000:
            score = 12 - (12 * (cost_efficiency_ratio / 2000))
            score = round(score * 2) / 2
            return max(0, score)
        else:
            return 0

    def calculate_os4p(params):
        """
        Computes key performance, emissions, and financial metrics for the OS4P system.
        Returns a dictionary with calculated results used by later visualizations.
        """
        # Unpack parameters
        num_outposts = params["num_outposts"]
        large_patrol_fuel = params["large_patrol_fuel"]
        rib_fuel = params["rib_fuel"]
        small_patrol_fuel = params["small_patrol_fuel"]
        hours_per_day_base = params["hours_per_day_base"]
        interest_rate = params["interest_rate"]
        loan_years = params["loan_years"]
        sla_premium = params["sla_premium"]
        operating_days_per_year = params["operating_days_per_year"]
        co2_factor = params["co2_factor"]
        maintenance_emissions = params["maintenance_emissions"]

        # CAPEX & OPEX Inputs:
        microgrid_capex = params["microgrid_capex"]
        drones_capex = params["drones_capex"]
        maintenance_opex = params["maintenance_opex"]
        communications_opex = params["communications_opex"]
        security_opex = params["security_opex"]

        # Fuel consumption and CO₂ emissions:
        diesel_generator_count = params.get("number_diesel_generators", 1)
        genset_fuel_per_day = params["genset_fuel_per_hour"] * params["genset_operating_hours"] * diesel_generator_count
        ms240_gd_fuel_per_day = params["num_ms240_gd_vehicles"] * params["ms240_gd_fuel_consumption"] * hours_per_day_base
        daily_fuel_consumption = (
            (params["num_large_patrol_boats"] * large_patrol_fuel +
             params["num_rib_boats"] * rib_fuel +
             params["num_small_patrol_boats"] * small_patrol_fuel) * hours_per_day_base
        ) + genset_fuel_per_day + ms240_gd_fuel_per_day
        annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year
        manned_co2_emissions = annual_fuel_consumption * co2_factor  # kg CO₂/year
        autonomous_co2_emissions = maintenance_emissions  # kg CO₂/year

        # CO₂ Avoidance:
        ghg_abs_avoidance_per_outpost = (manned_co2_emissions - autonomous_co2_emissions) / 1000  # tonnes CO₂/year
        ghg_abs_avoidance_all_outposts = ghg_abs_avoidance_per_outpost * num_outposts
        lifetime_years = params["lifetime_years"]
        ghg_abs_avoidance_lifetime = ghg_abs_avoidance_all_outposts * lifetime_years

        if manned_co2_emissions > 0:
            ghg_rel_avoidance = ((manned_co2_emissions - autonomous_co2_emissions) / manned_co2_emissions) * 100
        else:
            ghg_rel_avoidance = 0

        # Financial Calculations:
        total_capex_per_outpost = microgrid_capex + drones_capex
        total_capex = total_capex_per_outpost * num_outposts
        annual_opex_per_outpost = maintenance_opex + communications_opex + security_opex
        annual_opex = annual_opex_per_outpost * num_outposts
        lifetime_opex = annual_opex * loan_years

        pilot_markup = total_capex * 1.25
        non_unit_cost_pct = params.get("non_unit_cost_pct", 0)
        non_unit_cost = pilot_markup * (non_unit_cost_pct / 100)
        total_pilot_cost = pilot_markup + non_unit_cost

        grant_coverage = 0.60
        total_grant = grant_coverage * total_pilot_cost
        debt = total_pilot_cost - total_grant

        monthly_interest_rate = interest_rate / 100 / 12
        num_months = loan_years * 12
        monthly_debt_payment = (debt * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -num_months)
        lifetime_debt_payment = monthly_debt_payment * num_months

        sla_multiplier = 1 + sla_premium / 100
        monthly_fee_unit = ((monthly_debt_payment / num_outposts) + (annual_opex_per_outpost / 12)) * sla_multiplier
        annual_fee_unit = monthly_fee_unit * 12
        lifetime_fee_total = annual_fee_unit * num_outposts * loan_years

        payback_years = lifetime_debt_payment / (annual_fee_unit * num_outposts) if annual_fee_unit * num_outposts > 0 else float('inf')

        cost_efficiency_per_ton = total_grant / ghg_abs_avoidance_all_outposts if ghg_abs_avoidance_all_outposts > 0 else float('inf')
        cost_efficiency_lifetime = total_grant / ghg_abs_avoidance_lifetime if ghg_abs_avoidance_lifetime > 0 else float('inf')

        innovation_fund_score = calculate_innovation_fund_score(cost_efficiency_per_ton)
        innovation_fund_score_lifetime = calculate_innovation_fund_score(cost_efficiency_lifetime)

        tco = total_capex + lifetime_opex
        tco_per_outpost = tco / num_outposts

        # Levelized Cost of Energy (LCOE) Calculation:
        r = interest_rate / 100
        n = loan_years
        CRF = (r * (1 + r) ** n) / ((1 + r) ** n - 1) if ((1 + r) ** n - 1) != 0 else 0
        annualized_capex = total_capex_per_outpost * CRF
        annual_energy = params["annual_energy_production"]
        lcoe = (annualized_capex + annual_opex_per_outpost) / annual_energy

        capex_breakdown = {
            "Microgrid": microgrid_capex * num_outposts,
            "Drones": drones_capex * num_outposts,
        }

        result = {
            "ghg_abs_avoidance_per_outpost": ghg_abs_avoidance_per_outpost,
            "ghg_abs_avoidance_all_outposts": ghg_abs_avoidance_all_outposts,
            "ghg_abs_avoidance_lifetime": ghg_abs_avoidance_lifetime,
            "ghg_rel_avoidance": ghg_rel_avoidance,
            "daily_fuel_consumption": daily_fuel_consumption,
            "manned_co2_emissions": manned_co2_emissions,
            "autonomous_co2_emissions": autonomous_co2_emissions,
            "total_capex": total_capex,
            "total_capex_per_outpost": total_capex_per_outpost,
            "annual_opex": annual_opex,
            "annual_opex_per_outpost": annual_opex_per_outpost,
            "lifetime_opex": lifetime_opex,
            "tco": tco,
            "tco_per_outpost": tco_per_outpost,
            "monthly_debt_payment": monthly_debt_payment,
            "monthly_fee_unit": monthly_fee_unit,
            "annual_fee_unit": annual_fee_unit,
            "lifetime_fee_total": lifetime_fee_total,
            "cost_efficiency_per_ton": cost_efficiency_per_ton,
            "cost_efficiency_lifetime": cost_efficiency_lifetime,
            "innovation_fund_score": innovation_fund_score,
            "innovation_fund_score_lifetime": innovation_fund_score_lifetime,
            "pilot_markup": pilot_markup,
            "non_unit_cost": non_unit_cost,
            "total_pilot_cost": total_pilot_cost,
            "total_grant": total_grant,
            "debt": debt,
            "lifetime_debt_payment": lifetime_debt_payment,
            "lcoe": lcoe,
            "payback_years": payback_years,
            "capex_breakdown": capex_breakdown,
            "opex_breakdown": {
                "Maintenance": maintenance_opex * num_outposts,
                "Communications": communications_opex * num_outposts,
                "Security": security_opex * num_outposts
            },
            "co2_factors": {
                "Manned Emissions": manned_co2_emissions / 1000,
                "Autonomous Emissions": autonomous_co2_emissions / 1000
            },
            # For DCF analysis:
            "annual_revenue": annual_fee_unit * 12 * num_outposts,
            "annual_debt_service": monthly_debt_payment * 12
        }
        return result

    # ---------------------- DETAILED DISCOUNTED CASHFLOW ANALYSIS FUNCTION ---------------------- #
    def calculate_dcf_analysis(params, results):
        """
        Constructs a detailed year-by-year discounted cash flow (DCF) table for the entire project lifetime.
        Accounts for initial investment, annual revenues, OPEX, debt service, tax (if applicable), and depreciation.
        Returns the DCF table as a DataFrame, along with NPV and IRR.
        """
        lifetime = params["lifetime_years"]
        discount_rate = params["interest_rate"] / 100

        # Assume initial investment is the CAPEX at t=0 (negative cash flow)
        initial_investment = - (params["microgrid_capex"] + params["drones_capex"]) * params["num_outposts"]

        # Annual cash flow (base case): revenue minus OPEX and debt service.
        annual_cash_flow = results["annual_revenue"] - results["annual_opex"] - results["annual_debt_service"]

        # Build DCF table (year 0 is initial investment)
        dcf_table = []
        cumulative = initial_investment
        for year in range(0, lifetime + 1):
            if year == 0:
                cash_flow = initial_investment
            else:
                cash_flow = annual_cash_flow  # In a more detailed model, you might adjust for growth, tax, depreciation, etc.
            discount_factor = 1 / ((1 + discount_rate) ** year)
            discounted_cf = cash_flow * discount_factor
            # For cumulative, include t=0 only once and then add discounted flows for years > 0
            if year > 0:
                cumulative += discounted_cf
            dcf_table.append({
                "Year": year,
                "Undiscounted CF": cash_flow,
                "Discount Factor": discount_factor,
                "Discounted CF": discounted_cf,
                "Cumulative Discounted CF": cumulative
            })

        dcf_df = pd.DataFrame(dcf_table)
        npv = dcf_df["Discounted CF"].sum()
        try:
            irr = np.irr(dcf_df["Undiscounted CF"])
        except Exception:
            irr = np.nan

        return dcf_df, npv, irr

    # ---------------------- INTERACTIVE FINANCIAL VISUALIZATION FUNCTIONS ---------------------- #
    def create_dcf_charts(dcf_df):
        """
        Create interactive Plotly charts:
          - Comparison of Undiscounted vs. Discounted Cash Flows.
          - Cumulative Discounted Cash Flow.
        """
        year_list = dcf_df["Year"]
        undiscounted = dcf_df["Undiscounted CF"]
        discounted = dcf_df["Discounted CF"]
        cumulative = dcf_df["Cumulative Discounted CF"]

        # Annual cash flow comparison chart:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=year_list, y=undiscounted,
                                  mode="lines+markers",
                                  name="Undiscounted CF",
                                  line=dict(color="blue", dash="dot")))
        fig1.add_trace(go.Scatter(x=year_list, y=discounted,
                                  mode="lines+markers",
                                  name="Discounted CF",
                                  line=dict(color="green")))
        fig1.update_layout(title="Annual Cash Flow Comparison",
                           xaxis_title="Year",
                           yaxis_title="Cash Flow (€)",
                           hovermode="x unified")

        # Cumulative cash flow chart:
        fig2 = go.Figure(go.Bar(x=year_list, y=cumulative, name="Cumulative Discounted CF"))
        fig2.update_layout(title="Cumulative Discounted Cash Flow",
                           xaxis_title="Year",
                           yaxis_title="Cumulative Cash Flow (€)",
                           hovermode="x unified")
        return fig1, fig2

    # ---------------------- PDF REPORT GENERATION (Enhanced with DCF Analysis) ---------------------- #
    def generate_pdf(results, params, dcf_df, npv, irr):
        """
        Generate a PDF report including detailed financial metrics and the lifetime DCF analysis.
        """
        pdf = FPDF()
        pdf.unifontsubset = False
        pdf.add_page()
        pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "fonts/DejaVuSans-Bold.ttf", uni=True)

        # Title & Executive Summary
        pdf.set_font("DejaVu", "B", 16)
        pdf.cell(0, 10, "Green Sentinel OS4P - Executive Summary", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Overview Metrics", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"Total CAPEX (€): {results['total_capex']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Annual OPEX (€/year): {results['annual_opex']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Total Debt Financing (€): {results['debt']:,.0f}", ln=True)
        pdf.ln(5)

        # DCF Analysis Section
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Lifetime Discounted Cash Flow Analysis", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"Net Present Value (NPV): {npv:,.0f} €", ln=True)
        pdf.cell(0, 10, f"Internal Rate of Return (IRR): {irr*100 if np.isfinite(irr) else 0:.2f} %", ln=True)
        pdf.ln(5)

        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 10, "Year-by-Year Cash Flow Breakdown:", ln=True)
        pdf.set_font("DejaVu", "", 10)
        for index, row in dcf_df.iterrows():
            pdf.cell(0, 8, f"Year {int(row['Year'])}: Undisc. CF = {row['Undiscounted CF']:.0f}, "
                           f"Disc. CF = {row['Discounted CF']:.0f}, "
                           f"Cumulative = {row['Cumulative Discounted CF']:.0f}", ln=True)
        pdf.ln(5)

        # LCOE Section
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "LCOE Calculation", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"LCOE (€/kWh): {results['lcoe']:.4f}", ln=True)
        pdf.ln(5)

        pdf_bytes = pdf.output(dest="S").encode("latin1", errors="replace")
        return pdf_bytes

    # ---------------------- APPLICATION MAIN FUNCTION ---------------------- #
    def main():
        st.title("OS4P Green Sentinel")
        st.markdown("### Configure Your OS4P System Below")
        
        # Sidebar: User Inputs
        with st.sidebar:
            st.header("User Inputs")
            st.subheader("System Configuration")
            num_outposts = st.number_input("Number of Outposts", min_value=1, max_value=1000, value=100, step=1, format="%d")
            
            st.subheader("Vessel/Asset Count - Manned Scenario")
            num_large_patrol_boats = st.number_input("Large Patrol Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_rib_boats = st.number_input("RIB Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_small_patrol_boats = st.number_input("Small Patrol Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_ms240_gd_vehicles = st.number_input("M/S 240 GD Patrol Vehicles", min_value=0, max_value=100, value=1, step=1, format="%d")
            number_diesel_generators = st.number_input("Diesel Generators", min_value=1, max_value=50, value=1, step=1, format="%d")
            
            st.subheader("Fuel Consumption (Manned Scenario)")
            large_patrol_fuel = st.number_input("Large Patrol Boat Fuel (L/h)", min_value=50, max_value=300, value=150, step=10, format="%d")
            rib_fuel = st.number_input("RIB Boat Fuel (L/h)", min_value=10, max_value=100, value=50, step=5, format="%d")
            small_patrol_fuel = st.number_input("Small Patrol Boat Fuel (L/h)", min_value=5, max_value=50, value=30, step=5, format="%d")
            hours_per_day_base = st.number_input("Patrol Hours per Day", min_value=4, max_value=24, value=8, step=1, format="%d")
            
            st.subheader("Additional Fuel & Cost Parameters")
            ms240_gd_fuel_consumption = st.number_input("M/S 240 GD Vehicle Fuel (L/h)", min_value=0, max_value=25, value=15, step=10, format="%d")
            genset_fuel_per_hour = st.number_input("GENSET Fuel Consumption (L/h)", min_value=0.1, max_value=10.0, value=2.5, step=0.1, format="%.1f")
            genset_operating_hours = st.number_input("GENSET Operating Hours per Day", min_value=1, max_value=24, value=24, step=1, format="%d")
            
            st.subheader("Operational & Financial Parameters")
            operating_days_per_year = st.number_input("Operating Days per Year", min_value=50, max_value=365, value=180, step=1, format="%d")
            co2_factor = st.number_input("CO₂ Factor (kg CO₂ per liter)", min_value=0.5, max_value=5.0, value=2.63, step=0.1, format="%.1f")
            interest_rate = st.number_input("Interest Rate (%)", min_value=1.0, max_value=15.0, value=4.2, step=0.1, format="%.1f")
            loan_years = st.number_input("Loan Years", min_value=3, max_value=25, value=10, step=1, format="%d")
            sla_premium = st.number_input("SLA Premium (%)", min_value=0.0, max_value=50.0, value=10.0, step=1.0, format="%.1f")
            non_unit_cost_pct = st.number_input("Non-unit Cost (%)", min_value=0.0, max_value=100.0, value=25.0, step=0.1, format="%.1f")
            tax_rate = st.number_input("Corporate Tax Rate (%)", min_value=0.0, max_value=50.0, value=25.0, step=0.5, format="%.1f")
            
            st.subheader("Asset Lifetime & Emissions")
            lifetime_years = st.number_input("OS4P Unit Lifetime (years)", min_value=1, max_value=50, value=20, step=1, format="%d")
            maintenance_emissions = st.number_input("Maintenance Emissions (kg CO₂)", min_value=500, max_value=20000, value=1594, step=10, format="%d")
            st.subheader("Energy Production")
            annual_energy_production = st.number_input("Annual Energy Production (kWh/year)", min_value=1000, max_value=100000, value=20000, step=1000, format="%d")
            
            st.subheader("CAPEX Summary (€ per Outpost)")
            show_capex_detail = st.checkbox("Show detailed CAPEX breakdown", value=False)
            if show_capex_detail:
                st.markdown("#### Microgrid CAPEX Breakdown")
                st.markdown("##### Equipment CAPEX")
                solar_pv_capex = st.number_input("Solar PV System (10kWp)", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
                wind_turbine_capex = st.number_input("Wind Turbine (3kW)", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
                battery_capex = st.number_input("Battery Storage (30kWh)", min_value=10000, max_value=100000, value=36000, step=1000, format="%d")
                telecom_capex = st.number_input("Telecommunications", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
                microgrid_equipment = solar_pv_capex + wind_turbine_capex + battery_capex + telecom_capex
                st.markdown("##### BOS CAPEX")
                microgrid_transp = st.number_input("Transportation", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
                install_capex = st.number_input("Installation & Commissioning", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
                st.markdown("#### Other CAPEX")
                bos_contin = st.number_input("Additional BOS/Contingency CAPEX", min_value=0, max_value=100000, value=0, step=5000, format="%d")
                microgrid_bos = microgrid_transp + install_capex + bos_contin
                microgrid_capex = microgrid_equipment + microgrid_bos
                st.markdown(f"**Total Microgrid CAPEX: €{microgrid_capex:,}**")
                bos_capex = microgrid_bos
                st.markdown("#### Drone System CAPEX Breakdown")
                drone_units = st.number_input("Number of Drones per Outpost", min_value=1, max_value=10, value=3, step=1, format="%d")
                drone_unit_cost = st.number_input("Cost per Drone (€)", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
                drones_capex = drone_units * drone_unit_cost
                st.markdown(f"**Total Drones CAPEX: €{drones_capex:,}**")
                total_capex_per_outpost = microgrid_capex + drones_capex
                st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
            else:
                microgrid_capex = st.number_input("Microgrid CAPEX", min_value=50000, max_value=200000, value=110000, step=5000, format="%d")
                drones_capex = st.number_input("Drones CAPEX", min_value=20000, max_value=100000, value=60000, step=5000, format="%d")
                total_capex_per_outpost = microgrid_capex + drones_capex
                st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
            
            st.subheader("OPEX Inputs (€/Outpost/Year)")
            maintenance_opex = st.number_input("Maintenance OPEX", min_value=500, max_value=5000, value=2000, step=1000, format="%d")
            communications_opex = st.number_input("Communications OPEX", min_value=500, max_value=1500, value=1000, step=1000, format="%d")
            security_opex = st.number_input("Security OPEX", min_value=0, max_value=1000, value=0, step=1000, format="%d")
        
        # Pack parameters into a dictionary:
        params = {
            "num_outposts": num_outposts,
            "large_patrol_fuel": large_patrol_fuel,
            "rib_fuel": rib_fuel,
            "small_patrol_fuel": small_patrol_fuel,
            "hours_per_day_base": hours_per_day_base,
            "genset_fuel_per_hour": genset_fuel_per_hour,
            "genset_operating_hours": genset_operating_hours,
            "num_ms240_gd_vehicles": num_ms240_gd_vehicles,
            "ms240_gd_fuel_consumption": ms240_gd_fuel_consumption,
            "interest_rate": interest_rate,
            "loan_years": loan_years,
            "sla_premium": sla_premium,
            "non_unit_cost_pct": non_unit_cost_pct,
            "lifetime_years": lifetime_years,
            "operating_days_per_year": operating_days_per_year,
            "co2_factor": co2_factor,
            "maintenance_emissions": maintenance_emissions,
            "maintenance_opex": maintenance_opex,
            "communications_opex": communications_opex,
            "security_opex": security_opex,
            "annual_energy_production": annual_energy_production,
            "num_large_patrol_boats": num_large_patrol_boats,
            "num_rib_boats": num_rib_boats,
            "num_small_patrol_boats": num_small_patrol_boats,
            "number_diesel_generators": number_diesel_generators,
            "microgrid_capex": microgrid_capex,
            "drones_capex": drones_capex,
            "tax_rate": tax_rate
        }
        if show_capex_detail:
            params["detailed_capex"] = {
                "Solar PV (10kWp)": solar_pv_capex,
                "Wind Turbine (3kW)": wind_turbine_capex,
                "Battery Storage (30kWh)": battery_capex,
                "Telecommunications": telecom_capex,
                "Microgrid BOS": microgrid_bos,
                "Installation & Commissioning": install_capex,
                f"Drones ({drone_units}x)": drones_capex,
                "Additional BOS": bos_capex
            }
        
        # Compute system results:
        results = calculate_os4p(params)
        dcf_df, npv, irr = calculate_dcf_analysis(params, results)
        fig1, fig2 = create_dcf_charts(dcf_df)
        
        # ---------------------- TAB LAYOUT ---------------------- #
        tab_intro, tab_overview, tab_innovation, tab_financial, tab_lcoe, tab_visualizations, tab_sensitivity = st.tabs(
            ["Introduction", "Overview", "Innovation Fund Scoring", "Financial Analysis", "LCOE Calculation", "Visualizations", "Sensitivity Analysis"]
        )
        
        with tab_intro:
            st.header("Introduction")
            st.markdown("""
**OS4P Green Sentinel**

The project aims to reduce CO₂ emissions and enhance border security through the deployment of autonomous systems.
            """)
        
        with tab_financial:
            st.header("Financial Analysis")
            st.subheader("Financing Details")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total CAPEX (€)", f"{results['total_capex']:,.0f}")
                st.metric("Total OPEX (€)", f"{results['annual_opex']:,.0f}")
                st.metric("Total Debt (€)", f"{results['debt']:,.0f}")
            with col2:
                st.metric("Monthly Debt Payment (€)", f"{results['monthly_debt_payment']:,.0f}")
                st.metric("Lifetime Debt Payment (€)", f"{results['lifetime_debt_payment']:,.0f}")
            with col3:
                st.metric("Annual Fee/Outpost (€)", f"{results['annual_fee_unit']:,.0f}")
            st.markdown("#### Payback Period")
            st.metric("Payback Period (years)", f"{results['payback_years']:.1f}")
            
            st.markdown("---")
            st.subheader("Discounted Cashflow Analysis")
            st.plotly_chart(fig1, use_container_width=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(dcf_df)
            st.markdown(f"**NPV:** {npv:,.0f} €")
            st.markdown(f"**IRR:** {irr*100:.2f} %")
            
            # Optionally, add controls for scenario analysis:
            st.markdown("### Scenario Analysis")
            baseline = st.checkbox("Show Baseline Scenario", value=True)
            best_case = st.checkbox("Show Best Case Scenario", value=False)
            worst_case = st.checkbox("Show Worst Case Scenario", value=False)
            # (Additional processing for scenarios can be implemented here.)
        
        with tab_visualizations:
            st.header("Cost Breakdown & Emission Analysis")
            # [Additional visualizations can be added here.]
            
        # PDF Reporting Button
        if st.button("Generate PDF Report"):
            pdf_bytes = generate_pdf(results, params, None, dcf_df, npv, irr)
            st.download_button("Download PDF", pdf_bytes, file_name="OS4P_Report.pdf", mime="application/pdf")
    
    # Run the main function:
    if __name__ == '__main__':
        main()
