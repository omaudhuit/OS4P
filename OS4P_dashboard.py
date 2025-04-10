import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF  # pip install fpdf2
from PIL import Image  # Added for image handling

st.set_page_config(page_title="OS4P Green Sentinel", layout="wide")

# ---------------------- Video Playback on Startup ---------------------- #
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
    # ---------------------- Application Code Below ---------------------- #

    def calculate_innovation_fund_score(cost_efficiency_ratio):
        """
        Calculate Innovation Fund score based on cost efficiency ratio
        
        For INNOVFUND-2024-NZT-PILOTS topic:
        - If cost efficiency ratio is ≤ 2000 EUR/t CO₂-eq: Score = 12 - (12 × (ratio / 2000))
        - Otherwise: 0 points
        
        Returns rounded to the nearest half point (min 0, max 12)
        """
        if cost_efficiency_ratio <= 2000:
            score = 12 - (12 * (cost_efficiency_ratio / 2000))
            score = round(score * 2) / 2
            return max(0, score)
        else:
            return 0

    def calculate_os4p(params):
        # Extract user-defined constants from params
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

        # Aggregated CAPEX value
        total_capex_per_outpost = params["total_capex_per_outpost"]

        # OPEX Inputs
        maintenance_opex = params["maintenance_opex"]
        communications_opex = params["communications_opex"]
        security_opex = params["security_opex"]

        # Optional detailed CAPEX components (for visualization only)
        detailed_capex = params.get("detailed_capex", None)

        # Fuel consumption inputs for additional equipment
        diesel_generator_count = params.get("number_diesel_generators", 1)
        genset_fuel_per_day = params["genset_fuel_per_hour"] * params["genset_operating_hours"] * diesel_generator_count
        ms240_gd_fuel_per_day = params["num_ms240_gd_vehicles"] * params["ms240_gd_fuel_consumption"] * hours_per_day_base

        # Updated CO₂ Emissions Calculation:
        # Daily fuel consumption from vessel counts plus generator systems
        daily_fuel_consumption = (
            (params["num_large_patrol_boats"] * large_patrol_fuel +
             params["num_rib_boats"] * rib_fuel +
             params["num_small_patrol_boats"] * small_patrol_fuel) * hours_per_day_base
        ) + genset_fuel_per_day + ms240_gd_fuel_per_day

        annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year

        # Manned emissions based solely on the manned scenario inputs (kg CO₂/year)
        manned_co2_emissions = annual_fuel_consumption * co2_factor
        autonomous_co2_emissions = maintenance_emissions  # (kg CO₂/year)

        # Calculate total GHG Emission Avoidance (tonnes CO₂/year)
        ghg_abs_avoidance = (manned_co2_emissions - autonomous_co2_emissions) / 1000
        lifetime_years = params["lifetime_years"]
        ghg_abs_avoidance_lifetime = ghg_abs_avoidance * lifetime_years

        if manned_co2_emissions > 0:
            ghg_rel_avoidance = ((manned_co2_emissions - autonomous_co2_emissions) / manned_co2_emissions) * 100
        else:
            ghg_rel_avoidance = 0

        # NEW: Use a single total annual absolute avoidance value (remove per-outpost calculations)
        ghg_abs_avoidance_total = ghg_abs_avoidance

        # Financial Calculations using the CAPEX and OPEX values
        total_capex = total_capex_per_outpost * num_outposts
        annual_opex_per_outpost = maintenance_opex + communications_opex + security_opex
        annual_opex = annual_opex_per_outpost * num_outposts
        lifetime_opex = annual_opex * loan_years

        pilot_markup = total_capex * 1.25
        non_unit_cost_pct = params.get("non_unit_cost_pct", 0)
        non_unit_cost = pilot_markup * (non_unit_cost_pct / 100)
        total_pilot_cost = pilot_markup + non_unit_cost

        # Financing: 60% by grant, 40% by loan
        total_grant = 0.60 * total_pilot_cost
        debt = 0.40 * total_pilot_cost

        monthly_interest_rate = interest_rate / 100 / 12
        num_months = loan_years * 12
        monthly_debt_payment = (debt * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -num_months)
        lifetime_debt_payment = monthly_debt_payment * num_months

        sla_multiplier = 1 + sla_premium / 100
        monthly_fee_unit = ((monthly_debt_payment / num_outposts) + (annual_opex_per_outpost / 12)) * sla_multiplier
        annual_fee_unit = monthly_fee_unit * 12
        lifetime_fee_total = annual_fee_unit * num_outposts * loan_years

        if annual_fee_unit * num_outposts > 0:
            payback_years = lifetime_debt_payment / (annual_fee_unit * num_outposts)
        else:
            payback_years = float('inf')

        cost_efficiency_per_ton = total_grant / ghg_abs_avoidance_total if ghg_abs_avoidance_total > 0 else float('inf')
        cost_efficiency_lifetime = total_grant / ghg_abs_avoidance_lifetime if ghg_abs_avoidance_lifetime > 0 else float('inf')

        innovation_fund_score = calculate_innovation_fund_score(cost_efficiency_per_ton)
        innovation_fund_score_lifetime = calculate_innovation_fund_score(cost_efficiency_lifetime)

        tco = total_capex + lifetime_opex
        tco_per_outpost = tco / num_outposts

        r = interest_rate / 100
        n = loan_years
        CRF = (r * (1+r)**n) / ((1+r)**n - 1) if ((1+r)**n - 1) != 0 else 0
        annualized_capex = total_capex_per_outpost * CRF
        annual_energy = params["annual_energy_production"]
        lcoe = (annualized_capex + annual_opex_per_outpost) / annual_energy

        capex_breakdown = {
            "Total CAPEX": total_capex_per_outpost * num_outposts
        }

        result = {
            "ghg_abs_avoidance_total": ghg_abs_avoidance_total,
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
                "Manned Emissions (tonnes)": manned_co2_emissions / 1000,
                "Autonomous Emissions (tonnes)": autonomous_co2_emissions / 1000
            }
        }

        if detailed_capex:
            result["detailed_capex_breakdown"] = detailed_capex

        return result

    def perform_sensitivity_analysis(params, selected_param, range_values):
        import pandas as pd
        sensitivity_data = []
        for value in range_values:
            new_params = params.copy()
            new_params[selected_param] = value
            result = calculate_os4p(new_params)
            sensitivity_data.append({
                'Parameter_Value': value,
                'Absolute_Avoidance_Total': result['ghg_abs_avoidance_total'],
                'Manned_CO2_Emissions': result['manned_co2_emissions'],
                'Autonomous_CO2_Emissions': result['autonomous_co2_emissions'],
                'Relative_Avoidance': result['ghg_rel_avoidance']
            })
        return pd.DataFrame(sensitivity_data)

    def generate_pdf(results, params, lcoe_breakdown):
        pdf = FPDF()
        pdf.unifontsubset = False
        pdf.add_page()

        pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "fonts/DejaVuSans-Bold.ttf", uni=True)

        pdf.set_font("DejaVu", "B", 16)
        pdf.cell(0, 10, "“Green Sentinel” OS4P", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        pdf.set_font("DejaVu", "", 12)
        intro_text = (
            "The Green Sentinel (OS4P) project in Greece aims to significantly reduce CO₂ emissions through the deployment of Off-grid Smart Surveillance Security Sentinel Pylons (OSPs) and the integration of drones for continuous surveillance. "
            "Renewable Energy Generation and CO₂ Reduction: Each OSP unit is equipped with renewable energy systems that replace diesel generators and power autonomous drone systems, thereby reducing greenhouse gas emissions. "
            "A full summary of the impact is detailed below. "
            "Drone Integration for Surveillance and Additional CO₂ Savings: AI-driven drones offer a lower carbon footprint compared to traditional surveillance vehicles. "
            "Conclusion: By combining renewable energy with drone-based surveillance, the Green Sentinel project enhances operational efficiency and supports climate and decarbonization targets."
        )
        pdf.multi_cell(0, 10, intro_text)
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Overview Metrics", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"Total Absolute GHG Emission Avoidance (tCO₂e/year): {results['ghg_abs_avoidance_total']:.1f}", ln=True)
        pdf.cell(0, 10, f"Lifetime Absolute GHG Emission Avoidance (tCO₂e): {results['ghg_abs_avoidance_lifetime']:.1f}", ln=True)
        pdf.cell(0, 10, f"Relative GHG Emission Avoidance (%): {results['ghg_rel_avoidance']:.1f}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Cost Metrics", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"Total CAPEX (€): {results['total_capex']:,.0f}", ln=True)
        pdf.cell(0, 10, f"CAPEX per Outpost (€): {results['total_capex_per_outpost']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Annual OPEX (€/year): {results['annual_opex']:,.0f}", ln=True)
        pdf.cell(0, 10, f"OPEX per Outpost (€/year): {results['annual_opex_per_outpost']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Total Cost of Ownership (€): {results['tco']:,.0f}", ln=True)
        pdf.cell(0, 10, f"TCO per Outpost (€): {results['tco_per_outpost']:,.0f}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Financial Details", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"Total Pilot Cost with Markup (€): {results['pilot_markup']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Non-unit Cost (€): {results['non_unit_cost']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Total Pilot Cost (with Overhead) (€): {results['total_pilot_cost']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Grant Coverage (€): {results['total_grant']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Debt Financing Required (€): {results['debt']:,.0f}", ln=True)
        pdf.cell(0, 10, f"Payback Period (years): {results['payback_years']:.1f}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "LCOE Calculation", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"LCOE (€/kWh): {results['lcoe']:.4f}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 10, "Calculation Breakdown:", ln=True)
        pdf.set_font("DejaVu", "", 12)
        for index, row in lcoe_breakdown.iterrows():
            pdf.cell(0, 10, f"{row['Metric']}: {row['Value']:.2f}", ln=True)
        
        pdf_bytes = pdf.output(dest="S").encode("latin1", errors="replace")
        return pdf_bytes

    def create_cost_breakdown_chart(capex_breakdown, opex_breakdown, detailed_capex=None):
        import plotly.graph_objects as go
        labels = list(capex_breakdown.keys()) + list(opex_breakdown.keys())
        values = list(capex_breakdown.values()) + list(opex_breakdown.values())
        # Merge detailed CAPEX if provided
        if detailed_capex:
            labels += list(detailed_capex.keys())
            values += list(detailed_capex.values())
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        fig.update_layout(title="Cost Breakdown")
        return fig

    def create_co2_comparison_chart(co2_factors):
        import plotly.graph_objects as go
        labels = list(co2_factors.keys())
        values = list(co2_factors.values())
        fig = go.Figure(data=[go.Bar(x=labels, y=values, text=values, textposition='auto')])
        fig.update_layout(title="CO₂ Emissions Comparison", yaxis_title="Emissions (tonnes)")
        return fig

    def create_payback_period_chart(payback_years):
        import plotly.graph_objects as go
        fig = go.Figure()
        # Display the payback period as a labeled marker on a simple chart
        fig.add_trace(go.Scatter(
            x=[payback_years],
            y=[0],
            mode='markers+text',
            marker=dict(size=20, color='orange'),
            text=[f"{payback_years:.1f} years"],
            textposition='top center'
        ))
        fig.update_layout(
            title="Payback Period",
            xaxis_title="Payback Period (Years)",
            yaxis=dict(visible=False),
            showlegend=False
        )
        return fig

    def main():
        st.title("OS4P Green Sentinel")
        st.markdown("### Configure Your OS4P System Below")
        
        with st.sidebar:
            st.header("User Inputs")
            st.subheader("System Configuration")
            num_outposts = st.number_input("Number of Outposts - Autonomous OS4P", min_value=1, max_value=1000, value=100, step=1, format="%d")
            
            st.subheader("Vessel/Asset Count - Manned Scenario")
            num_large_patrol_boats = st.number_input("Number of Large Patrol Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_rib_boats = st.number_input(
                "Number of RIB Boats", 
                min_value=0, max_value=10, value=1, step=1, format="%d", 
                key="num_rib_boats_vessels"
            )
            num_small_patrol_boats = st.number_input("Number of Small Patrol Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_ms240_gd_vehicles = st.number_input("Number of M/S 240 GD Patrol Vehicles", min_value=0, max_value=100, value=1, step=1, format="%d")
            
            # Input for diesel generators
            number_diesel_generators = st.number_input("Number of Diesel Generators", min_value=1, max_value=50, value=1, step=1, format="%d")
           
            st.subheader("Fuel Consumption (Liters per Hour) - Manned Scenario")
            large_patrol_fuel = st.number_input("Large Patrol Boat Fuel (L/h)", min_value=50, max_value=300, value=150, step=10, format="%d")
            rib_fuel = st.number_input(
                "RIB Boat Fuel (L/h)", 
                min_value=10, max_value=100, value=50, step=5, format="%d", 
                key="rib_boat_fuel"
            )
            small_patrol_fuel = st.number_input("Small Patrol Boat Fuel (L/h)", min_value=5, max_value=50, value=30, step=5, format="%d")
        
            hours_per_day_base = st.number_input("Patrol Hours per Day", min_value=4, max_value=24, value=8, step=1, format="%d")
                   
            st.subheader("Additional Fuel Consumption Parameters")
            ms240_gd_fuel_consumption = st.number_input("M/S 240 GD Patrol Vehicle Fuel Consumption (L/h)", min_value=0, max_value=25, value=15, step=10, format="%d")
            diesel_generator_capex = st.number_input("Diesel Generator CAPEX (€)", min_value=10000, max_value=200000, value=50000, step=5000, format="%d")
            diesel_generator_opex = st.number_input("Diesel Generator Annual OPEX (€)", min_value=1000, max_value=20000, value=3000, step=500, format="%d")
            diesel_fuel_cost = st.number_input("Diesel Fuel Cost (€/liter)", min_value=0.5, max_value=2.0, value=1.5, step=0.1, format="%.1f")
            diesel_generator_efficiency = st.number_input("Diesel Generator Efficiency (kWh per liter)", min_value=0.1, max_value=5.0, value=2.5, step=0.1, format="%.1f")
            genset_fuel_per_hour = st.number_input("GENSET Fuel Consumption per Hour (L/h)", min_value=0.1, max_value=10.0, value=2.5, step=0.1, format="%.1f")
            genset_operating_hours = st.number_input("GENSET Operating Hours per Day", min_value=1, max_value=24, value=24, step=1, format="%d")
            
            st.subheader("Operational Parameters")
            operating_days_per_year = st.number_input("Operating Days per Year", min_value=50, max_value=365, value=180, step=1, format="%d")
            co2_factor = st.number_input("CO₂ Factor (kg CO₂ per liter)", min_value=0.5, max_value=5.0, value=2.63, step=0.1, format="%.1f")
            
            st.subheader("Financial Parameters")
            interest_rate = st.number_input("Interest Rate (%)", min_value=1.0, max_value=15.0, value=4.2, step=0.1, format="%.1f")
            loan_years = st.number_input("Project Loan Years (for financial calculations)", min_value=3, max_value=25, value=10, step=1, format="%d")
            sla_premium = st.number_input("SLA Premium (%)", min_value=0.0, max_value=50.0, value=10.0, step=1.0, format="%.1f")
            non_unit_cost_pct = st.number_input("Non-unit Cost (%)", min_value=0.0, max_value=100.0, value=25.0, step=0.1, format="%.1f")
            
            st.subheader("Asset Lifetime")
            lifetime_years = st.number_input("OS4P Unit Lifetime (years)", min_value=1, max_value=50, value=10, step=1, format="%d")
            
            st.subheader("OS4P Emissions")
            maintenance_emissions = st.number_input("Maintenance Emissions (kg CO₂)", min_value=500, max_value=20000, value=1594, step=10, format="%d")
                  
            st.subheader("Energy Production")
            annual_energy_production = st.number_input(
                "Annual Energy Production per Outpost (kWh/year)", 
                min_value=1000, 
                max_value=100000, 
                value=20000, 
                step=1000, 
                format="%d"
            )
            
            st.subheader("CAPEX Summary (€ per Outpost)")
            show_capex_detail = st.checkbox("Show detailed CAPEX breakdown", value=False)

            if show_capex_detail:
                st.markdown("#### Detailed CAPEX Breakdown")
                solar_pv_capex = st.number_input("Solar PV System (10kWp)", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
                wind_turbine_capex = st.number_input("Wind Turbine (3kW)", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
                battery_capex = st.number_input("Battery Storage (30kWh)", min_value=10000, max_value=100000, value=36000, step=1000, format="%d")
                telecom_capex = st.number_input("Telecommunications", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
                bos_micro_capex = st.number_input("Microgrid BOS", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
                install_capex = st.number_input("Installation & Commissioning", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
                
                st.markdown("#### Drone System CAPEX Breakdown")
                drone_units = st.number_input("Number of Drones per Outpost", min_value=1, max_value=10, value=3, step=1, format="%d")
                drone_unit_cost = st.number_input("Cost per Drone (€)", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
                drones_capex_detail = drone_units * drone_unit_cost
                
                st.markdown("#### Other CAPEX")
                bos_capex = st.number_input("Additional BOS/CONTINGENCY/OTHER CAPEX", min_value=0, max_value=100000, value=0, step=5000, format="%d")
                
                # Aggregated CAPEX is the sum of all detailed components:
                total_capex_per_outpost = (solar_pv_capex + wind_turbine_capex + battery_capex +
                                           telecom_capex + bos_micro_capex + install_capex +
                                           drones_capex_detail + bos_capex)
                st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
                
                # Compute individual CAPEX components:
                microgrid_capex = solar_pv_capex + wind_turbine_capex + battery_capex + telecom_capex + bos_micro_capex + install_capex
                drones_capex = drones_capex_detail
            else:
                total_capex_per_outpost = st.number_input("Total CAPEX per Outpost", min_value=50000, max_value=500000, value=110000, step=5000, format="%d")
                detailed_capex = None
                # Fallback values:
                microgrid_capex = total_capex_per_outpost
                drones_capex = 0
                bos_capex = 0
            
            st.subheader("OPEX Inputs (€ per Outpost per Year)")
            maintenance_opex = st.number_input("Maintenance OPEX", min_value=500, max_value=5000, value=2000, step=1000, format="%d")
            communications_opex = st.number_input("Communications OPEX", min_value=500, max_value=1500, value=1000, step=1000, format="%d")
            security_opex = st.number_input("Security OPEX", min_value=0, max_value=1000, value=0, step=1000, format="%d")
        
        # Build parameters dictionary:
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
            # Save aggregated CAPEX per outpost:
            "total_capex_per_outpost": total_capex_per_outpost
        }

        if show_capex_detail:
            params["microgrid_capex"] = microgrid_capex
            params["drones_capex"] = drones_capex
            params["bos_capex"] = bos_capex
            params["detailed_capex"] = {
                "Solar PV (10kWp)": solar_pv_capex,
                "Wind Turbine (3kW)": wind_turbine_capex,
                "Battery Storage (30kWh)": battery_capex,
                "Telecommunications": telecom_capex,
                "Microgrid BOS": bos_micro_capex,
                "Installation & Commissioning": install_capex,
                f"Drones ({drone_units}x)": drones_capex_detail,
                "Additional BOS": bos_capex
            }
        else:
            params["microgrid_capex"] = microgrid_capex
            params["drones_capex"] = drones_capex
            params["bos_capex"] = bos_capex

        results = calculate_os4p(params)
        
        # Define your tabs:
        tab_intro, tab_overview, tab_innovation, tab_financial, tab_financial_model, tab_lcoe, tab_visualizations, tab_sensitivity = st.tabs(
            ["Introduction", "Overview", "Innovation Fund Scoring Framework", "Financial Details", "Financial Model", "LCOE Calculation", "Visualizations", "Sensitivity Analysis"]
        )
        
        with tab_intro:
            st.header("Introduction")
            st.markdown("""
            ****OS4P Green Sentinel****
            
            [Introduction text here...]
            """)
            os4p_image = Image.open("OS4P-The Island.png")
            st.image(os4p_image, caption="OS4P Green Sentinel Installation Overview", use_container_width=True)

        with tab_overview:
            st.subheader("Coverage Calculation")
            land_borders = st.number_input("Enter area for Land Borders (km²)", value=500, min_value=0, step=1)
            territorial_waters = st.number_input("Enter area for Territorial Waters (km²)", value=40000, min_value=0, step=1)
            forest_area = st.number_input("Enter area for Forest Area (km²)", value=2000, min_value=0, step=1)
            total_area = land_borders + territorial_waters + forest_area
            coverage_per_unit = st.number_input("Enter coverage area per OS4P unit (km²)", value=30, min_value=1, step=1)
            required_units = int(np.ceil(total_area / coverage_per_unit))
            st.markdown(f"**Total area to cover: {total_area} km²**")
            st.markdown(f"**Coverage per OS4P unit: {coverage_per_unit} km²**")
            st.markdown(f"**Required OS4P Units: {required_units}**")
            
            st.subheader("Environmental Impact")
            col_em1, col_em2 = st.columns(2)
            with col_em1:
                st.metric("Manned Emissions (tonnes/year)", f"{results['manned_co2_emissions']/1000:.1f}")
            with col_em2:
                st.metric("Autonomous Emissions (tonnes/year)", f"{results['autonomous_co2_emissions']/1000:.1f}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Absolute GHG Emission Avoidance (tCO₂e/year)", f"{results['ghg_abs_avoidance_total']:.1f}")
            with col2:
                st.metric("Lifetime Absolute GHG Emission Avoidance (tCO₂e)", f"{results['ghg_abs_avoidance_lifetime']:.1f}")
            with col3:
                st.metric("Relative GHG Emission Avoidance (%)", f"{results['ghg_rel_avoidance']:.1f}")
            
            st.subheader("Cost Overview")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total CAPEX (€)", f"{results['total_capex']:,.0f}")
                st.metric("CAPEX per Outpost (€)", f"{results['total_capex_per_outpost']:,.0f}")
            with col2:
                st.metric("Annual OPEX (€/year)", f"{results['annual_opex']:,.0f}")
                st.metric("OPEX per Outpost (€/year)", f"{results['annual_opex_per_outpost']:,.0f}")
            with col3:
                st.metric("Total Cost of Ownership (€)", f"{results['tco']:,.0f}")
                st.metric("TCO per Outpost (€)", f"{results['tco_per_outpost']:,.0f}")
        
        with tab_innovation:
            st.subheader("Efficiency Metrics & Innovation Fund Score")
            with st.expander("Innovation Fund Scoring Criteria"):
                st.markdown("""
                **Innovation Fund Scoring for Cost Efficiency (INNOVFUND-2024-NZT-PILOTS)**
                
                - If cost efficiency ratio ≤ 2000 EUR/t CO₂-eq:  
                  Score = 12 - (12 × (ratio / 2000))
                - Otherwise: Score = 0  
                
                Result is rounded to the nearest half point. A lower ratio yields a higher score.
                """)
            col1, col2 = st.columns(2)
            with col1:
                ce_yearly = results['cost_efficiency_per_ton']
                ce_yearly_str = f"{ce_yearly:,.0f}" if ce_yearly != float('inf') else "∞"
                st.metric("Cost per Tonne CO₂ Saved (€/tonne/year)", ce_yearly_str)
                score_color = "green" if results['innovation_fund_score'] >= 9 else ("orange" if results['innovation_fund_score'] >= 6 else "red")
                st.markdown(f"<h3 style='color: {score_color}'>Innovation Fund Score: {results['innovation_fund_score']}/12</h3>", unsafe_allow_html=True)
                st.progress((results['innovation_fund_score'] / 12))
            with col2:
                ce_lifetime = results['cost_efficiency_lifetime']
                ce_lifetime_str = f"{ce_lifetime:,.0f}" if ce_lifetime != float('inf') else "∞"
                st.metric("Lifetime Cost per Tonne CO₂ Saved (€/tonne)", ce_lifetime_str)
                score_lifetime_color = "green" if results['innovation_fund_score_lifetime'] >= 9 else ("orange" if results['innovation_fund_score_lifetime'] >= 6 else "red")
                st.markdown(f"<h3 style='color: {score_lifetime_color}'>Lifetime Score: {results['innovation_fund_score_lifetime']}/12</h3>", unsafe_allow_html=True)
                st.progress((results['innovation_fund_score_lifetime'] / 12))
            
            st.markdown("### Detailed Scoring Framework for PILOT Projects (INNOVFUND-2024-NZT-PILOTS)")
            st.markdown("""
            [Detailed criteria text here...]
            """)
            
            st.markdown("### Enter Your Scores")
            degree_innovation = st.slider("Degree of Innovation (9-15)", min_value=9, max_value=15, value=12)
            project_maturity = st.slider("Project Maturity (0-15)", min_value=0, max_value=15, value=10)
            replicability = st.slider("Replicability (0-15)", min_value=0, max_value=15, value=10)
            bonus_points = st.slider("Bonus Points (0-4)", min_value=0, max_value=4, value=2)
            
            lifetime_years = params["lifetime_years"]
            threshold_abs = 1000 * (lifetime_years / 10)
            ghg_abs = results["ghg_abs_avoidance_lifetime"]
            absolute_score = min(2, 2 * (ghg_abs / threshold_abs))
            ghg_rel = results["ghg_rel_avoidance"]
            relative_score = 5 if ghg_rel >= 75 else 0
            quality_score = 0
            if ghg_rel >= 75:
                quality_score = 3 + 2 * min(1, (ghg_rel - 75) / 25)
            ghg_emission_avoidance_score = absolute_score + relative_score + quality_score
            
            innovation_fund_score = results["innovation_fund_score"]
            if innovation_fund_score == float('inf'):
                cost_efficiency_score = 0
            else:
                cost_efficiency_score = (innovation_fund_score / 12) * 15
            
            total_innovation_score = (degree_innovation * 2) + ghg_emission_avoidance_score + project_maturity + replicability + cost_efficiency_score + bonus_points
            
            st.markdown("### Calculated Scores")
            st.write(f"**Degree of Innovation (weighted):** {degree_innovation * 2:.1f} (Input: {degree_innovation})")
            st.write(f"**GHG Emission Avoidance Potential:** {ghg_emission_avoidance_score:.1f} (Absolute: {absolute_score:.1f}, Relative: {relative_score}, Quality: {quality_score:.1f})")
            st.write(f"**Project Maturity:** {project_maturity:.1f}")
            st.write(f"**Replicability:** {replicability:.1f}")
            st.write(f"**Cost Efficiency Score:** {cost_efficiency_score:.1f} (Calculated from cost efficiency ratio)")
            st.write(f"**Bonus Points:** {bonus_points:.1f}")
            st.write(f"**Total Innovation Fund Score:** {total_innovation_score:.1f} (Maximum without bonus: 87, with bonus: 91)")
        
        with tab_financial:
            st.subheader("Financing Details")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pilot Cost with Markup (€)", f"{results['pilot_markup']:,.0f}")
                st.metric("Non-unit Cost (€)", f"{results['non_unit_cost']:,.0f}")
                st.metric("Total Pilot Cost (Markup + Overhead) (€)", f"{results['total_pilot_cost']:,.0f}")
                st.metric("Grant Coverage (€)", f"{results['total_grant']:,.0f}")
                st.metric("Debt Financing Required (€)", f"{results['debt']:,.0f}")
            with col2:
                st.metric("Monthly Debt Payment (€)", f"{results['monthly_debt_payment']:,.0f}")
                st.metric("Lifetime Debt Payment (€)", f"{results['lifetime_debt_payment']:,.0f}")
            with col3:
                st.metric("Monthly Fee per Outpost (€)", f"{results['monthly_fee_unit']:,.0f}")
                st.metric("Annual Fee per Outpost (€)", f"{results['annual_fee_unit']:,.0f}")
                st.metric("Lifetime Total Fee (€)", f"{results['lifetime_fee_total']:,.0f}")
            
            st.markdown("#### Payback Analysis")
            st.metric("Payback Period (years)", f"{results['payback_years']:.1f}")
        
        with tab_financial_model:
            st.header("Discounted Cash Flow Analysis")
            st.markdown("""
            Once the pilot is constructed, cashflows are generated by the monthly fee per outpost + maintenance fees per outpost.
            The Total Pilot Cost is financed 60% by the grant and 40% with the loan.
            """)
            discount_rate = interest_rate / 100
            years = loan_years
            # Use the loan amount as the initial investment
            initial_investment = results["debt"]
            
            # Cashflows generated by monthly fee and maintenance fees (maintenance fees become revenue)
            annual_revenue = (results["monthly_fee_unit"] * 12 * num_outposts) + (maintenance_opex * num_outposts)
            annual_debt_service = results["monthly_debt_payment"] * 12
            annual_cash_flow = annual_revenue - annual_debt_service
            st.metric("Annual Cash Flow (€)", f"{annual_cash_flow:,.0f}")
            
            npv = -initial_investment
            discounted_cash_flows = []
            for t in range(1, years + 1):
                discounted_cf = annual_cash_flow / ((1 + discount_rate) ** t)
                discounted_cash_flows.append(discounted_cf)
                npv += discounted_cf
            st.metric("NPV (€)", f"{npv:,.0f}")
            
            year_list = list(range(1, years + 1))
            undiscounted_cash_flows = [annual_cash_flow] * years
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=year_list,
                y=undiscounted_cash_flows,
                mode='lines+markers',
                name='Undiscounted Cash Flow',
                line=dict(color='blue', dash='dot')
            ))
            fig.add_trace(go.Scatter(
                x=year_list,
                y=discounted_cash_flows,
                mode='lines+markers',
                name='Discounted Cash Flow',
                line=dict(color='green')
            ))
            fig.update_layout(
                title='Discounted Cash Flow Analysis',
                xaxis_title='Year',
                yaxis_title='Cash Flow (€)',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
            dcf_table = pd.DataFrame({
                "Year": year_list,
                "Discounted Cash Flow (€)": discounted_cash_flows,
                "Undiscounted Cash Flow (€)": undiscounted_cash_flows
            })
            st.table(dcf_table)
        
        with tab_lcoe:
            st.header("LCOE Calculation")
            st.markdown("""
            **Levelized Cost of Electricity (LCOE) = (Annualized CAPEX per Outpost + Annual OPEX per Outpost) / Annual Energy Production per Outpost**
            """)
            st.metric("LCOE (€/kWh)", f"{results['lcoe']:.4f}")
            
            r = interest_rate / 100
            n = loan_years
            CRF = (r * (1+r)**n) / ((1+r)**n - 1) if ((1+r)**n - 1) != 0 else 0
            total_capex_per_outpost_calc = params["microgrid_capex"] + params["drones_capex"] + params["bos_capex"]
            annualized_capex = total_capex_per_outpost_calc * CRF
            annual_opex_per_outpost = results["annual_opex_per_outpost"]
            annual_energy = annual_energy_production
            lcoe_breakdown = pd.DataFrame({
                "Metric": ["Annualized CAPEX per Outpost (€/year)", "Annual OPEX per Outpost (€/year)", "Annual Energy Production (kWh/year)"],
                "Value": [annualized_capex, annual_opex_per_outpost, annual_energy]
            })
            st.markdown("**Calculation Breakdown:**")
            st.table(lcoe_breakdown)

            # Diesel Generator LCOE Calculation
            annualized_capex_diesel = diesel_generator_capex * CRF
            annual_fuel_consumption_diesel = params["genset_fuel_per_hour"] * params["genset_operating_hours"] * operating_days_per_year
            annual_fuel_cost = annual_fuel_consumption_diesel * diesel_fuel_cost
            diesel_opex_total = diesel_generator_opex
            total_annualized_capex_diesel = annualized_capex_diesel * number_diesel_generators
            total_diesel_opex = diesel_opex_total * number_diesel_generators
            total_annual_fuel_cost = annual_fuel_cost * number_diesel_generators
            annual_total_cost_diesel = total_annualized_capex_diesel + total_diesel_opex + total_annual_fuel_cost
            annual_electricity_diesel = annual_fuel_consumption_diesel * diesel_generator_efficiency
            annual_electricity_diesel_total = annual_electricity_diesel * number_diesel_generators
            lcoe_diesel = annual_total_cost_diesel / annual_electricity_diesel_total if annual_electricity_diesel_total > 0 else float('inf')
            
            st.markdown("### Diesel Generator LCOE Calculation")
            st.metric("Diesel Generator LCOE (€/kWh)", f"{lcoe_diesel:.4f}")
            diesel_lcoe_breakdown = pd.DataFrame({
                "Metric": [
                    "Annualized CAPEX (€/year)",
                    "Annual OPEX (€/year)",
                    "Annual Fuel Cost (€/year)",
                    "Annual Total Cost (€/year)",
                    "Annual Electricity Production (kWh/year)"
                ],
                "Value": [
                    annualized_capex_diesel,
                    diesel_generator_opex,
                    annual_fuel_cost,
                    annual_total_cost_diesel,
                    annual_electricity_diesel_total
                ]
            })
            st.markdown("**Diesel Generator LCOE Breakdown:**")
            st.table(diesel_lcoe_breakdown)
        
        with tab_visualizations:
            st.subheader("Cost Breakdown Visualization")
            if "detailed_capex_breakdown" in results:
                cost_chart = create_cost_breakdown_chart(results["capex_breakdown"], results["opex_breakdown"], detailed_capex=results["detailed_capex_breakdown"])
            else:
                cost_chart = create_cost_breakdown_chart(results["capex_breakdown"], results["opex_breakdown"])
            st.plotly_chart(cost_chart)
            
            st.subheader("CO₂ Emissions Comparison")
            co2_chart = create_co2_comparison_chart(results["co2_factors"])
            st.plotly_chart(co2_chart)
            
            st.subheader("Payback Period")
            payback_chart = create_payback_period_chart(results["payback_years"])
            st.plotly_chart(payback_chart)
        
        with tab_sensitivity:
            st.subheader("CO₂ Emissions Sensitivity Analysis")
            
            sensitivity_param_options = {
                "large_patrol_fuel": "Large Patrol Boat Fuel (L/h)",
                "rib_fuel": "RIB Boat Fuel (L/h)",
                "small_patrol_fuel": "Small Patrol Boat Fuel (L/h)",
                "hours_per_day_base": "Patrol Hours per Day",
                "operating_days_per_year": "Operating Days per Year",
                "co2_factor": "CO₂ Factor (kg CO₂/L)",
                "maintenance_emissions": "Maintenance Emissions (kg CO₂)"
            }
            
            sensitivity_settings = {
                "large_patrol_fuel": {"min": 50, "max": 300, "step": 25},
                "rib_fuel": {"min": 10, "max": 100, "step": 10},
                "small_patrol_fuel": {"min": 5, "max": 50, "step": 5},
                "hours_per_day_base": {"min": 4, "max": 24, "step": 2},
                "operating_days_per_year": {"min": 200, "max": 365, "step": 20},
                "co2_factor": {"min": 0.5, "max": 3.0, "step": 0.25},
                "maintenance_emissions": {"min": 500, "max": 5000, "step": 500}
            }
            
            col1, col2 = st.columns([2, 3])
            with col1:
                selected_param = st.selectbox(
                    "Parameter to analyze:",
                    list(sensitivity_param_options.keys()),
                    format_func=lambda x: sensitivity_param_options[x]
                )
                setting = sensitivity_settings[selected_param]
                min_val_default = setting["min"]
                max_val_default = setting["max"]
                step = setting["step"]
                default_val = params.get(selected_param, min_val_default)
                
                min_range = st.number_input("Minimum value:", value=min_val_default, step=step)
                max_range = st.number_input("Maximum value:", value=max_val_default, step=step)
                num_steps = st.number_input("Number of data points:", value=10, min_value=5, max_value=20, step=1)
            
            with col2:
                if min_range >= max_range:
                    st.error("Minimum value must be less than maximum value!")
                else:
                    range_values = np.linspace(min_range, max_range, int(num_steps))
                    if selected_param in ["hours_per_day_base", "operating_days_per_year"]:
                        range_values = range_values.astype(int)
                    sensitivity_results = perform_sensitivity_analysis(params, selected_param, range_values)
                    st.markdown("#### Sensitivity Analysis Results:")
                    format_dict = {
                        'Parameter_Value': '{:.2f}' if selected_param == "co2_factor" else '{:.0f}',
                        'Absolute_Avoidance_Total': '{:.2f}', 
                        'Manned_CO2_Emissions': '{:.2f}',
                        'Autonomous_CO2_Emissions': '{:.2f}',
                        'Relative_Avoidance': '{:.2f}'
                    }
                    st.dataframe(sensitivity_results.style.format(format_dict))
            
            st.markdown("#### Sensitivity Analysis Visualizations")
            col1, col2 = st.columns(2)
            with col1:
                avoidance_chart = create_sensitivity_chart(
                    sensitivity_results, 
                    sensitivity_param_options[selected_param],
                    'Absolute_Avoidance_Total', 
                    'Total Absolute GHG Emission Avoidance (tCO₂e/year)'
                )
                st.plotly_chart(avoidance_chart, use_container_width=True)
            with col2:
                emissions_chart = create_emissions_sensitivity_chart(
                    sensitivity_results,
                    sensitivity_param_options[selected_param]
                )
                st.plotly_chart(emissions_chart, use_container_width=True)
            
            st.markdown("#### Innovation Fund Score Sensitivity")
            innovation_score_chart = create_innovation_fund_score_chart(
                sensitivity_results,
                sensitivity_param_options[selected_param]
            )
            st.plotly_chart(innovation_score_chart, use_container_width=True)

            st.markdown("#### Combined Sensitivity Analysis")
            combined_chart = create_combined_sensitivity_graph(
                sensitivity_results,
                sensitivity_param_options[selected_param]
            )
            st.plotly_chart(combined_chart, use_container_width=True)
            
            st.markdown("""
            This chart shows how the Innovation Fund score changes with the parameter value. 
            Higher scores (closer to 12) improve funding chances. Scores use the formula:

            **Score = 12 - (12 × cost efficiency ratio / 2000)** when ratio ≤ 2000 EUR/t, otherwise 0.
            """)
            
            st.subheader("Multi-Parameter Impact Analysis")
            st.markdown("Analyze the impact of multiple parameters simultaneously:")
            analyze_patrol_fuel = st.checkbox("Patrol Boat Fuel Consumption", value=True)
            analyze_operations = st.checkbox("Operational Parameters", value=True)
            analyze_emissions = st.checkbox("Emissions Parameters", value=True)
            
            variation_pct = st.slider("Parameter Variation (%)", min_value=5, max_value=50, value=20, step=5,
                                  help="Percentage variation from the base case")
            
            def calculate_impact(param):
                params_high = params.copy()
                params_low = params.copy()
                params_high[param] = params[param] * (1 + variation_pct / 100)
                params_low[param] = params[param] * (1 - variation_pct / 100)
                high_result = calculate_os4p(params_high)
                low_result = calculate_os4p(params_low)
                return {
                    'Parameter': sensitivity_param_options.get(param, param),
                    'Low_Value': low_result['ghg_abs_avoidance_total'] - base_avoidance,
                    'High_Value': high_result['ghg_abs_avoidance_total'] - base_avoidance
                }
            
            if st.button("Run Multi-Parameter Analysis"):
                tornado_data = []
                base_result = calculate_os4p(params)
                base_avoidance = base_result['ghg_abs_avoidance_total']
                
                if analyze_patrol_fuel:
                    for param in ["large_patrol_fuel", "rib_fuel"]:
                        tornado_data.append(calculate_impact(param))
                
                if analyze_operations:
                    for param in ["operating_days_per_year", "hours_per_day_base"]:
                        tornado_data.append(calculate_impact(param))
                
                if analyze_emissions:
                    for param in ["co2_factor", "maintenance_emissions"]:
                        tornado_data.append(calculate_impact(param))
                
                if tornado_data:
                    tornado_df = pd.DataFrame(tornado_data)
                    tornado_df['Total_Impact'] = tornado_df['High_Value'].abs() + tornado_df['Low_Value'].abs()
                    tornado_df = tornado_df.sort_values('Total_Impact', ascending=False)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        y=tornado_df['Parameter'],
                        x=tornado_df['High_Value'],
                        name='Positive Impact',
                        orientation='h',
                        marker=dict(color='#66b3ff')
                    ))
                    fig.add_trace(go.Bar(
                        y=tornado_df['Parameter'],
                        x=tornado_df['Low_Value'],
                        name='Negative Impact',
                        orientation='h',
                        marker=dict(color='#ff9999')
                    ))
                    fig.update_layout(
                        title=f'Tornado Chart: Impact on Total Absolute GHG Emission Avoidance (±{variation_pct}% variation)',
                        xaxis_title='Change in Total Absolute GHG Emission Avoidance (tCO₂e/year)',
                        barmode='overlay',
                        legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'),
                        margin=dict(l=100)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown(f"""
                    ### Interpretation:
                    - This chart shows sensitivity of total GHG avoidance to parameter changes.
                    - Longer bars indicate greater impact.
                    - Blue bars: increase by {variation_pct}%
                    - Red bars: decrease by {variation_pct}%
                    """)
                    st.subheader("Parameter Elasticity")
                    st.markdown("""
                    This measures the responsiveness (elasticity) of GHG avoidance to a 1% change in each parameter.
                    Higher absolute values mean more influence.
                    """)
                    tornado_df['Elasticity'] = (tornado_df['High_Value'] / base_avoidance) / (variation_pct / 100)
                    elasticity_df = tornado_df[['Parameter', 'Elasticity']].sort_values('Elasticity', ascending=False, key=abs)
                    st.dataframe(elasticity_df.style.format({'Elasticity': '{:.3f}'}))
                else:
                    st.warning("Please select at least one parameter group to analyze.")
        
        r = interest_rate / 100
        n = loan_years
        CRF = (r * (1+r)**n) / ((1+r)**n - 1) if ((1+r)**n - 1) != 0 else 0
        total_capex_per_outpost_calc = params["microgrid_capex"] + params["drones_capex"] + params["bos_capex"]
        annualized_capex = total_capex_per_outpost_calc * CRF
        annual_opex_per_outpost = results["annual_opex_per_outpost"]
        annual_energy = annual_energy_production
        lcoe_breakdown = pd.DataFrame({
            "Metric": ["Annualized CAPEX per Outpost (€/year)", "Annual OPEX per Outpost (€/year)", "Annual Energy Production (kWh/year)"],
            "Value": [annualized_capex, annual_opex_per_outpost, annual_energy]
        })
        
        pdf_bytes = generate_pdf(results, params, lcoe_breakdown)
        st.download_button(label="Download Executive Summary", data=pdf_bytes, file_name="OS4P_Report.pdf", mime="application/pdf")

    if __name__ == "__main__":
        main()
