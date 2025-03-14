import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF  # pip install fpdf2
from PIL import Image  # Added for image handling   
import numpy_financial as npf  # NEW: For IRR calculation

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
        - If cost efficiency ratio is <= 2000 EUR/t CO₂-eq: 12 - (12 × (ratio / 2000))
        - If cost efficiency ratio is > 2000 EUR/t CO₂-eq: 0 points
        
        Returns rounded to nearest half point, min 0, max 12
        """
        if cost_efficiency_ratio <= 2000:
            score = 12 - (12 * (cost_efficiency_ratio / 2000))
            score = round(score * 2) / 2
            return max(0, score)
        else:
            return 0

    def calculate_os4p(params):
        # Extracting user-defined constants
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

        # CAPEX & OPEX Inputs
        microgrid_capex = params["microgrid_capex"]
        drones_capex = params["drones_capex"]
        maintenance_opex = params["maintenance_opex"]
        communications_opex = params["communications_opex"]
        security_opex = params["security_opex"]

        # Include the diesel generator count in fuel consumption calculation
        diesel_generator_count = params.get("number_diesel_generators", 1)
        # Updated CO₂ Emissions Calculation (Including GENSET and M/S 240 GD vehicles)
        genset_fuel_per_day = params["genset_fuel_per_hour"] * params["genset_operating_hours"] * diesel_generator_count
        ms240_gd_fuel_per_day = params["num_ms240_gd_vehicles"] * params["ms240_gd_fuel_consumption"] * hours_per_day_base
        daily_fuel_consumption = (
            (params["num_large_patrol_boats"] * large_patrol_fuel +
             params["num_rib_boats"] * rib_fuel +
             params["num_small_patrol_boats"] * small_patrol_fuel) * hours_per_day_base
        ) + genset_fuel_per_day + ms240_gd_fuel_per_day
        annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year
        manned_co2_emissions = annual_fuel_consumption * co2_factor  # in kg CO₂ per year
        autonomous_co2_emissions = maintenance_emissions  # in kg CO₂ per year

        # Split CO₂ Emission Avoidance into Absolute and Relative (in tonnes)
        ghg_abs_avoidance_per_outpost = (manned_co2_emissions - autonomous_co2_emissions) / 1000
        ghg_abs_avoidance_all_outposts = ghg_abs_avoidance_per_outpost * num_outposts
        lifetime_years = params["lifetime_years"]
        ghg_abs_avoidance_lifetime = ghg_abs_avoidance_all_outposts * lifetime_years

        if manned_co2_emissions > 0:
            ghg_rel_avoidance = ((manned_co2_emissions - autonomous_co2_emissions) / manned_co2_emissions) * 100
        else:
            ghg_rel_avoidance = 0

        # Financial Calculations
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

        if annual_fee_unit * num_outposts > 0:
            payback_years = lifetime_debt_payment / (annual_fee_unit * num_outposts)
        else:
            payback_years = float('inf')

        cost_efficiency_per_ton = total_grant / ghg_abs_avoidance_all_outposts if ghg_abs_avoidance_all_outposts > 0 else float('inf')
        cost_efficiency_lifetime = total_grant / ghg_abs_avoidance_lifetime if ghg_abs_avoidance_lifetime > 0 else float('inf')
        
        innovation_fund_score = calculate_innovation_fund_score(cost_efficiency_per_ton)
        innovation_fund_score_lifetime = calculate_innovation_fund_score(cost_efficiency_lifetime)
        
        tco = total_capex + lifetime_opex
        tco_per_outpost = tco / num_outposts

        r = interest_rate / 100
        n = loan_years
        if (1+r)**n - 1 != 0:
            CRF = (r * (1+r)**n) / ((1+r)**n - 1)
        else:
            CRF = 0
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
            }
        }
        
        return result

    def create_cost_breakdown_chart(capex_data, opex_data):
        capex_df = pd.DataFrame(list(capex_data.items()), columns=['Category', 'Value'])
        capex_df['Type'] = 'CAPEX'
        opex_df = pd.DataFrame(list(opex_data.items()), columns=['Category', 'Value'])
        opex_df['Type'] = 'OPEX (Annual)'
        combined_df = pd.concat([capex_df, opex_df])
        
        fig = px.bar(
            combined_df, 
            x='Category', 
            y='Value', 
            color='Type', 
            title='Cost Breakdown', 
            labels={'Value': 'Cost (€)', 'Category': ''}
        )
        fig.update_layout(barmode='group')
        return fig

    def create_co2_comparison_chart(co2_data):
        labels = list(co2_data.keys())
        values = list(co2_data.values())
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color=['#ff9999', '#66b3ff']
        )])
        fig.update_layout(
            title_text='CO₂ Emissions Comparison (tonnes/year)',
            yaxis_title='CO₂ (tonnes)',
        )
        savings = values[0] - values[1]
        savings_percentage = (savings / values[0]) * 100 if values[0] > 0 else 0
        fig.add_annotation(
            x=0.5,
            y=max(values) * 1.1,
            text=f"Savings: {savings:.1f} tonnes ({savings_percentage:.1f}%)",
            showarrow=False,
            font=dict(size=14)
        )
        return fig

    def create_payback_period_chart(payback_years):
        display_value = payback_years if payback_years != float('inf') else 0
        gauge_range = [0, max(10, display_value + 1)]
        fig = go.Figure(go.Indicator(
            mode="number+gauge",
            value=display_value,
            title={"text": "Payback Period (years)"},
            gauge={'axis': {'range': gauge_range},
                   'bar': {'color': "darkblue"}}
        ))
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        return fig

    def perform_sensitivity_analysis(base_params, sensitivity_param, range_values):
        results = []
        for value in range_values:
            params = base_params.copy()
            params[sensitivity_param] = value
            result = calculate_os4p(params)
            results.append({
                'Parameter_Value': value,
                'Absolute_Avoidance_Per_Outpost': result['ghg_abs_avoidance_per_outpost'],
                'Absolute_Avoidance_All_Outposts': result['ghg_abs_avoidance_all_outposts'],
                'Manned_CO2_Emissions': result['manned_co2_emissions'] / 1000,
                'Autonomous_CO2_Emissions': result['autonomous_co2_emissions'] / 1000,
                'Relative_Avoidance': result['ghg_rel_avoidance'],
                'Cost_Efficiency': result['cost_efficiency_per_ton'],
                'Innovation_Fund_Score': result['innovation_fund_score']
            })
        return pd.DataFrame(results)

    def create_sensitivity_chart(sensitivity_data, param_name, y_column, y_label):
        fig = px.line(
            sensitivity_data, 
            x='Parameter_Value', 
            y=y_column,
            markers=True,
            title=f'Sensitivity of {y_label} to {param_name}',
            labels={'Parameter_Value': param_name, y_column: y_label}
        )
        fig.update_layout(
            xaxis_title=param_name,
            yaxis_title=y_label,
            hovermode="x unified"
        )
        return fig

    def create_innovation_fund_score_chart(sensitivity_data, param_name):
        innovation_scores = []
        for index, row in sensitivity_data.iterrows():
            if row['Absolute_Avoidance_All_Outposts'] > 0:
                ce_ratio = 500000 / row['Absolute_Avoidance_All_Outposts']
                score = calculate_innovation_fund_score(ce_ratio)
            else:
                score = 0
            innovation_scores.append(score)
        
        score_data = sensitivity_data.copy()
        score_data['Innovation_Fund_Score'] = innovation_scores
        
        fig = px.line(
            score_data,
            x='Parameter_Value',
            y='Innovation_Fund_Score',
            markers=True,
            title=f'Innovation Fund Score Sensitivity to {param_name}',
            labels={'Parameter_Value': param_name, 'Innovation_Fund_Score': 'Innovation Fund Score (0-12)'}
        )
        
        fig.add_hline(y=9, line_dash="dash", line_color="green", annotation_text="Excellent (≥9)", 
                     annotation_position="top right")
        fig.add_hline(y=6, line_dash="dash", line_color="orange", annotation_text="Good (≥6)", 
                     annotation_position="top right")
        fig.add_hline(y=3, line_dash="dash", line_color="red", annotation_text="Marginal (≥3)", 
                     annotation_position="top right")
        
        fig.update_layout(
            xaxis_title=param_name,
            yaxis_title='Innovation Fund Score',
            yaxis=dict(range=[0, 12]),
            hovermode="x unified"
        )
        
        return fig

    # NEW: Combined Sensitivity Analysis Function
    def create_combined_sensitivity_graph(sensitivity_data, param_name):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sensitivity_data['Parameter_Value'],
            y=sensitivity_data['Absolute_Avoidance_All_Outposts'],
            mode='lines+markers',
            name='Absolute GHG Avoidance (tCO₂e/year)',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=sensitivity_data['Parameter_Value'],
            y=sensitivity_data['Manned_CO2_Emissions'],
            mode='lines+markers',
            name='Manned CO₂ Emissions (tonnes/year)',
            line=dict(color='red')
        ))
        fig.add_trace(go.Scatter(
            x=sensitivity_data['Parameter_Value'],
            y=sensitivity_data['Innovation_Fund_Score'],
            mode='lines+markers',
            name='Innovation Fund Score',
            line=dict(color='green')
        ))
        fig.update_layout(
            title=f'Combined Sensitivity Analysis for {param_name}',
            xaxis_title=param_name,
            yaxis_title='Value',
            hovermode='x unified'
        )
        return fig

    def create_emissions_sensitivity_chart(sensitivity_data, param_name):
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=sensitivity_data['Parameter_Value'],
            y=sensitivity_data['Manned_CO2_Emissions'],
            mode='lines+markers',
            name='Manned Emissions',
            line=dict(color='#ff9999', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=sensitivity_data['Parameter_Value'],
            y=sensitivity_data['Autonomous_CO2_Emissions'],
            mode='lines+markers',
            name='Autonomous Emissions',
            line=dict(color='#66b3ff', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=sensitivity_data['Parameter_Value'],
            y=sensitivity_data['Manned_CO2_Emissions'],
            mode='lines',
            name='Emission Avoidance',
            fill='tonexty',
            fillcolor='rgba(0, 255, 0, 0.2)',
            line=dict(width=0)
        ))
        
        fig.update_layout(
            title=f'CO₂ Emissions Sensitivity to {param_name}',
            xaxis_title=param_name,
            yaxis_title='CO₂ Emissions (tonnes/year)',
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig

    def generate_pdf(results, params, lcoe_breakdown, dcf_df, npv_value, irr_value, payback):
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
            "The Green Sentinel (OS4P) project in Greece aims to significantly reduce CO₂ emissions through the deployment of Offgrid Smart Surveillance Security Sentinel Pylons (OSPs) and the integration of drones for continuous surveillance. "
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
        pdf.cell(0, 10, f"Absolute GHG Emission Avoidance per Outpost (tCO₂e/year): {results['ghg_abs_avoidance_per_outpost']:.1f}", ln=True)
        pdf.cell(0, 10, f"Total Absolute GHG Emission Avoidance (tCO₂e/year): {results['ghg_abs_avoidance_all_outposts']:.1f}", ln=True)
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
        pdf.cell(0, 10, f"Payback Period (years): {payback if payback is not None else 'Not achieved'}", ln=True)
        
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
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Lifetime Cash Flow Analysis", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"NPV (Euros): {npv_value:,.0f}", ln=True)
        irr_formatted = f"{irr_value*100:.2f}" if irr_value is not None and not np.isnan(irr_value) else "N/A"
        pdf.cell(0, 10, f"IRR (%): {irr_formatted}", ln=True)
        pdf.cell(0, 10, f"Payback Period (years): {payback if payback is not None else 'Not achieved'}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 10, "Detailed Cash Flow Table:", ln=True)
        pdf.set_font("DejaVu", "", 10)
        # Add a few rows from the DCF table for summary (full table omitted for brevity)
        for index, row in dcf_df.head(5).iterrows():
            pdf.cell(0, 8, f"Year {int(row['Year'])}: Revenue={row['Revenue (€)']:.0f}, FCFF={row['FCFF (€)']:.0f}, Cumulative={row['Cumulative CF (€)']:.0f}", ln=True)
        pdf.cell(0, 8, "See full report for complete cash flow details.", ln=True)
        
        pdf_bytes = pdf.output(dest="S").encode("latin1", errors="replace")
        return pdf_bytes

    def main():
        st.title("OS4P Green Sentinel")
        st.markdown("### Configure Your OS4P System Below")
        
        with st.sidebar:
            st.header("User Inputs")
            st.subheader("System Configuration")
            num_outposts = st.number_input("Number of Outposts - Autonomous OS4P", min_value=1, max_value=1000, value=100, step=1, format="%d")
            
            st.subheader("Vessel/Asset Count - Manned Scenario")
            num_large_patrol_boats = st.number_input("Number of Large Patrol Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_rib_boats = st.number_input("Number of RIB Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_small_patrol_boats = st.number_input("Number of Small Patrol Boats", min_value=0, max_value=10, value=1, step=1, format="%d")
            num_ms240_gd_vehicles = st.number_input("Number of M/S 240 GD Patrol Vehicles", min_value=0, max_value=100, value=1, step=1, format="%d")
            
            # NEW: Add input for the number of diesel generators
            number_diesel_generators = st.number_input("Number of Diesel Generators", min_value=1, max_value=50, value=1, step=1, format="%d")
           
            st.subheader("Fuel Consumption (Liters per Hour) - Manned Scenario")
            large_patrol_fuel = st.number_input("Large Patrol Boat Fuel (L/h)", min_value=50, max_value=300, value=150, step=10, format="%d")
            rib_fuel = st.number_input("RIB Boat Fuel (L/h)", min_value=10, max_value=100, value=50, step=5, format="%d")
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
            lifetime_years = st.number_input("OS4P Unit Lifetime (years)", min_value=1, max_value=50, value=20, step=1, format="%d")
            
            st.subheader("OS4P Emissions")
            maintenance_emissions = st.number_input(
                "Maintenance Emissions (kg CO₂)", 
                min_value=500, 
                max_value=20000, 
                value=1594, 
                step=10, 
                format="%d"
            )
                  
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
                st.markdown("#### Microgrid CAPEX Breakdown")
                st.markdown("##### Equipment CAPEX")
                solar_pv_capex = st.number_input(
                    "Solar PV System (10kWp)", 
                    min_value=5000, max_value=50000, 
                    value=15000, step=1000, format="%d"
                )
                wind_turbine_capex = st.number_input(
                    "Wind Turbine (3kW)", 
                    min_value=5000, max_value=50000, 
                    value=12000, step=1000, format="%d"
                )
                battery_capex = st.number_input(
                    "Battery Storage (30kWh)", 
                    min_value=10000, max_value=100000, 
                    value=36000, step=1000, format="%d"
                )
                telecom_capex = st.number_input(
                    "Telecommunications", 
                    min_value=5000, max_value=50000, 
                    value=15000, step=1000, format="%d"
                )
  
                microgrid_equipment = solar_pv_capex + wind_turbine_capex + battery_capex + telecom_capex

                st.markdown("##### BOS CAPEX")
                microgrid_transp = st.number_input(
                    "Transportation", 
                    min_value=5000, max_value=50000, 
                    value=20000, step=1000, format="%d"
                )

                install_capex = st.number_input(
                    "Installation & Commissioning", 
                    min_value=5000, max_value=50000, 
                    value=12000, step=1000, format="%d"
                )

                st.markdown("#### Other CAPEX")
                bos_contin = st.number_input(
                    "Additional BOS/CONTINGENCY CAPEX", 
                    min_value=0, max_value=100000, 
                    value=0, step=5000, format="%d"
                )

                microgrid_bos = microgrid_transp + install_capex + bos_contin

                microgrid_capex = microgrid_equipment + microgrid_bos

                st.markdown(f"**Total Microgrid CAPEX: €{microgrid_capex:,}**")
                
                # (Assumes that microgrid_capex has been computed earlier from the detailed breakdown,
                #  and that microgrid_bos is its BOS component. Define bos_capex for consistency.)
                bos_capex = microgrid_bos  
                
                st.markdown("#### Drone System CAPEX Breakdown")
                drone_units = st.number_input(
                    "Number of Drones per Outpost", 
                    min_value=1, max_value=10, 
                    value=3, step=1, format="%d"
                )
                drone_unit_cost = st.number_input(
                    "Cost per Drone (€)", 
                    min_value=5000, max_value=50000, 
                    value=20000, step=1000, format="%d"
                )
                drones_capex = drone_units * drone_unit_cost
                st.markdown(f"**Total Drones CAPEX: €{drones_capex:,}**")
                
                total_capex_per_outpost = microgrid_capex + drones_capex
                st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
            else:
                microgrid_capex = st.number_input(
                    "Microgrid CAPEX", 
                    min_value=50000, max_value=200000, 
                    value=110000, step=5000, format="%d"
                )
                drones_capex = st.number_input(
                    "Drones CAPEX", 
                    min_value=20000, max_value=100000, 
                    value=60000, step=5000, format="%d"
                )

                total_capex_per_outpost = microgrid_capex + drones_capex
                st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
         
            st.subheader("OPEX Inputs (€ per Outpost per Year)")
            maintenance_opex = st.number_input("Maintenance OPEX", min_value=500, max_value=5000, value=2000, step=1000, format="%d")
            communications_opex = st.number_input("Communications OPEX", min_value=500, max_value=1500, value=1000, step=1000, format="%d")
            security_opex = st.number_input("Security OPEX", min_value=0, max_value=1000, value=0, step=1000, format="%d")
        
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
            # NEW: Include the diesel generator count in parameters
            "number_diesel_generators": number_diesel_generators,
        }
        
        if show_capex_detail:
            params["microgrid_capex"] = microgrid_capex
            params["drones_capex"] = drones_capex
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
        else:
            params["microgrid_capex"] = microgrid_capex
            params["drones_capex"] = drones_capex
        
        results = calculate_os4p(params)
        
        # Define tabs with the combined Financial Analysis tab
        tab_intro, tab_overview, tab_innovation, tab_financial, tab_lcoe, tab_visualizations, tab_sensitivity = st.tabs(
            ["Introduction", "Overview", "Innovation Fund Scoring Framework", "Financial Analysis", "LCOE Calculation", "Visualizations", "Sensitivity Analysis"]
        )

        with tab_intro:
            st.header("Introduction")
            st.markdown("""
            ****OS4P Green Sentinel****
            
            Problem Statement
            
            The European Union faces increasing pressures from climate change and escalating geopolitical challenges, particularly around border security and critical infrastructure resilience. Traditional surveillance methods and power solutions for remote outposts and border checkpoints predominantly rely on diesel generators and manned patrol operations. These conventional approaches:
            
             - Contribute significantly to greenhouse gas emissions, exacerbating climate change impacts.
             - Suffer from logistical vulnerabilities, such as fuel supply disruptions in conflict-prone or extreme weather-affected regions.
             - Offer limited resilience, leading to infrastructural vulnerabilities during extreme weather or crises.
             - Lack scalability, hindering expansion and modernization of surveillance and secure communication capabilities.
            
            Consequently, there is an urgent need for integrated, autonomous, and sustainable energy solutions to support border security and enhance civil protection across the EU while aligning with stringent climate and environmental targets.
            
            Solution: Green Sentinel (OS4P)
            
            The Green Sentinel solution involves deploying autonomous Off-grid Smart Surveillance Security Sentinel Pylons (OS4P), integrating renewable energy generation, energy storage systems, drone-based surveillance, AI-driven monitoring, and secure telecommunications.
            """)
            
            os4p_image = Image.open("OS4P-The Island.png")
            st.image(os4p_image, caption="OS4P Green Sentinel Installation Overview", use_container_width=True)

        with tab_overview:
            st.subheader("Coverage Calculation")
            st.markdown("The following inputs define the areas that need to be covered. The **coverage area per OS4P unit** is based on the specifications of the Drone system used.")
            land_borders = st.number_input("Enter area for Land Borders (km²)", value=500, min_value=0, step=1)
            territorial_waters = st.number_input("Enter area for Territorial Waters (km²)", value=40000, min_value=0, step=1)
            forest_area = st.number_input("Enter area for Forest Area (km²)", value=2000, min_value=0, step=1)
            total_area = land_borders + territorial_waters + forest_area
            coverage_per_unit = st.number_input("Enter coverage area per OS4P unit (km²)", value=30, min_value=1, step=1)
            required_units = int(np.ceil(total_area / coverage_per_unit))
            st.markdown(f"**Total area to cover: {total_area} km²**")
            st.markdown(f"**Coverage area per OS4P unit (based on the Drone system specifications): {coverage_per_unit} km²**")
            st.markdown(f"**Required OS4P Units: {required_units}**")
            
            st.subheader("Environmental Impact")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Absolute GHG Emission Avoidance per Outpost (tCO₂e/year)", f"{results.get('ghg_abs_avoidance_per_outposts', results['ghg_abs_avoidance_per_outpost']):.1f}")
            with col2:
                st.metric("Total Absolute GHG Emission Avoidance (tCO₂e/year)", f"{results['ghg_abs_avoidance_all_outposts']:.1f}")
            with col3:
                st.metric("Lifetime Absolute GHG Emission Avoidance (tCO₂e)", f"{results['ghg_abs_avoidance_lifetime']:.1f}")
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
                
                The Innovation Fund uses the following formula to score projects based on cost efficiency:
                - If cost efficiency ratio ≤ 2000 EUR/t CO₂-eq:  
                  Score = 12 - (12 × (cost efficiency ratio / 2000))
                - If cost efficiency ratio > 2000 EUR/t CO₂-eq:  
                  Score = 0 
                
                The result is rounded to the nearest half point. The minimum score is 0, maximum is 12.
                
                *A lower cost efficiency ratio (less EUR per tonne of CO₂ saved) results in a higher score.*
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
            - **Degree of Innovation**
              - Evaluates how much the project goes beyond incremental improvements (e.g. breakthrough or disruptive innovation).
              - **Score range:** 9 to 15 points, with a weight factor of 2.
            - **GHG Emission Avoidance Potential**
              - **Absolute GHG Emission Avoidance:** Up to 2 points (assesses the difference between the project’s total GHG emissions and those in the reference scenario over 10 years).
              - **Relative GHG Emission Avoidance:** Up to 5 points (based on the ratio of avoided emissions relative to the reference scenario).
              - **Quality of the GHG Emission Avoidance Calculation and Minimum Requirements:** Scores between 3 and 5 points, ensuring the calculation is robust and meets the minimum thresholds (for instance, a minimum relative avoidance of 75% for PILOT projects).
              - **Overall contribution:** Up to 12 points.
            - **Project Maturity**
              - Considers three sub-criteria:
                - **Technical Maturity:** 3 to 5 points, reflecting the feasibility and technological readiness.
                - **Financial Maturity:** 3 to 5 points, assessing the ability to reach financial close.
                - **Operational Maturity:** 3 to 5 points, evaluating the project’s implementation plan, track record, and risk mitigation strategies.
              - **Combined contribution:** Up to 15 points.
            - **Replicability**
              - Evaluated through:
                - **Efficiency gains and multiple environmental impacts:** Up to 5 points.
                - **Further deployment potential:** Up to 5 points.
                - **Contribution to Europe’s industrial leadership and competitiveness:** Up to 5 points.
              - **Total replicability:** Up to 15 points.
            - **Cost Efficiency**
              - Assessed by:
                - **Cost efficiency ratio:** Up to 12 points.
                - **Quality of the cost calculation and adherence to minimum requirements:** Scored from 1.5 to 3 points.
              - **Total contribution:** Up to 15 points.
            - **Bonus Points**
              - Four bonus items available, each contributing up to 1 point.
              - **Total bonus:** Up to 4 points.
            - **Total Scoring**
              - **Without bonus points:** Maximum score is 87.
              - **With bonus points:** Maximum score is 91.
              - **Note:** Proposals must meet the minimum pass score for each criterion/sub-criterion.
            """)
            
            st.markdown("### Enter Your Scores")
            degree_innovation = st.slider("Degree of Innovation (9-15)", min_value=9, max_value=15, value=12)
            project_maturity = st.slider("Project Maturity (0-15)", min_value=0, max_value=15, value=10)
            replicability = st.slider("Replicability (0-15)", min_value=0, max_value=15, value=10)
            bonus_points = st.slider("Bonus Points (0-4)", min_value=0, max_value=4, value=2)
            
            # Calculate GHG Emission Avoidance Potential Score based on environmental impact:
            lifetime_years = params["lifetime_years"]
            threshold_abs = 1000 * (lifetime_years / 10)  # threshold scales with lifetime
            ghg_abs = results["ghg_abs_avoidance_lifetime"]
            absolute_score = min(2, 2 * (ghg_abs / threshold_abs))
            ghg_rel = results["ghg_rel_avoidance"]
            relative_score = 5 if ghg_rel >= 75 else 0
            quality_score = 0
            if ghg_rel >= 75:
                quality_score = 3 + 2 * min(1, (ghg_rel - 75) / 25)
            ghg_emission_avoidance_score = absolute_score + relative_score + quality_score
            
            # Calculate Cost Efficiency Score: scale innovation_fund_score (0-12) to 0-15.
            innovation_fund_score = results["innovation_fund_score"]
            if innovation_fund_score == float('inf'):
                cost_efficiency_score = 0
            else:
                cost_efficiency_score = (innovation_fund_score / 12) * 15
            
            # Total Innovation Fund Score Calculation:
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
            st.header("Financial Analysis")

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
            
            st.markdown("---")
            st.subheader("Discounted Cash Flow Analysis")
            discount_rate = interest_rate / 100
            years = loan_years
            initial_investment = (params["microgrid_capex"] + params["drones_capex"]) * num_outposts
            annual_revenue = results["annual_fee_unit"] * 12 * num_outposts
            annual_opex = results["annual_opex"]
            annual_debt_service = results["monthly_debt_payment"] * 12
            # Simple DCF section (updated):
            annual_cash_flow = annual_revenue + annual_opex - annual_debt_service
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

            st.subheader("Detailed Discounted Cash Flow Analysis")
        
            # NEW: Detailed DCF model over the project lifetime (using unlevered free cash flow)
            discount_rate = interest_rate / 100
            lifetime = lifetime_years
            
            # Compute initial CAPEX (at t=0)
            total_capex = params["microgrid_capex"] * params["num_outposts"] + params["drones_capex"] * params["num_outposts"]
            cashflows = [-total_capex]
            dcf_data = []
            cumulative_cf = -total_capex

            # Ensure the following inputs are defined
            tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=50.0, value=25.0, step=0.5, format="%.1f")/100
            revenue_growth_rate = st.number_input("Revenue Growth Rate (%)", min_value=0.0, max_value=20.0, value=2.0, step=0.5, format="%.1f")/100
            opex_growth_rate = st.number_input("OPEX Growth Rate (%)", min_value=0.0, max_value=20.0, value=1.0, step=0.5, format="%.1f")/100
            depreciation_period = st.number_input("Depreciation Period (years)", min_value=1, max_value=lifetime_years, value=loan_years, step=1, format="%d")

            for t in range(1, lifetime + 1):
                # Calculate annual revenue with growth; revenue is based on the fee per outpost
                annual_revenue = results["annual_fee_unit"] * 12 * params["num_outposts"] * ((1 + revenue_growth_rate) ** (t-1))
                
                # OPEX is now treated as additional revenue (customer-side income), growing over time
                annual_opex = results["annual_opex"] * ((1 + opex_growth_rate) ** (t-1))
                
                # Depreciation is applied for the first 'depreciation_period' years
                depreciation = total_capex / depreciation_period if t <= depreciation_period else 0
                
                # EBIT is now computed as revenue plus additional OPEX revenue, less depreciation
                EBIT = annual_revenue + annual_opex - depreciation
                
                # Compute taxes only if EBIT is positive
                taxes = tax_rate * EBIT if EBIT > 0 else 0
                
                # Free Cash Flow to the Firm: add back depreciation after subtracting taxes
                FCFF = EBIT - taxes + depreciation
                
                # Discount the FCFF to present value
                df = (1 + discount_rate) ** (-t)
                discounted_fcff = FCFF * df
                
                cumulative_cf += discounted_fcff
                cashflows.append(FCFF)
                dcf_data.append({
                    "Year": t,
                    "Revenue (€)": annual_revenue,
                    "OPEX (€)": annual_opex,
                    "Depreciation (€)": depreciation,
                    "EBIT (€)": EBIT,
                    "Taxes (€)": taxes,
                    "FCFF (€)": FCFF,
                    "Discount Factor": df,
                    "Discounted FCFF (€)": discounted_fcff,
                    "Cumulative CF (€)": cumulative_cf
                })

            dcf_df = pd.DataFrame(dcf_data)
            st.markdown("**Detailed Cash Flow Table:**")
            st.dataframe(dcf_df.style.format({
                "Revenue (€)": "{:,.0f}",
                "OPEX (€)": "{:,.0f}",
                "Depreciation (€)": "{:,.0f}",
                "EBIT (€)": "{:,.0f}",
                "Taxes (€)": "{:,.0f}",
                "FCFF (€)": "{:,.0f}",
                "Discount Factor": "{:.3f}",
                "Discounted FCFF (€)": "{:,.0f}",
                "Cumulative CF (€)": "{:,.0f}"
            }))

            # Calculate NPV and IRR based on the FCFF series
            npv_value = npf.npv(discount_rate, [-total_capex] + list(dcf_df["FCFF (€)"]))
            irr_value = npf.irr([-total_capex] + list(dcf_df["FCFF (€)"]))

            # Calculate payback period based on discounted cash flows
            cum_cash = -total_capex
            payback = None
            for index, row in dcf_df.iterrows():
                cum_cash += row["Discounted FCFF (€)"]
                if cum_cash >= 0:
                    payback = row["Year"]
                    break

            st.metric("NPV (€)", f"{npv_value:,.0f}")
            st.metric("IRR (%)", f"{irr_value*100:.2f}" if irr_value is not None else "N/A")
            st.metric("Payback Period (years)", f"{payback if payback is not None else 'Not achieved'}")
            
            # NEW: Interactive Financial Visualizations
            st.markdown("#### Interactive DCF Visualizations")
            vis_option = st.selectbox("Select Chart:", ["Annual FCFF (Undiscounted vs Discounted)", "Cumulative Cash Flow"])
            
            if vis_option == "Annual FCFF (Undiscounted vs Discounted)":
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=dcf_df["Year"],
                    y=dcf_df["FCFF (€)"],
                    name="Undiscounted FCFF",
                    marker_color="blue"
                ))
                fig.add_trace(go.Scatter(
                    x=dcf_df["Year"],
                    y=dcf_df["Discounted FCFF (€)"],
                    mode="lines+markers",
                    name="Discounted FCFF",
                    line=dict(color="green")
                ))
                fig.update_layout(
                    title="Annual FCFF: Undiscounted vs Discounted",
                    xaxis_title="Year",
                    yaxis_title="FCFF (€)",
                    hovermode="x"
                )
                st.plotly_chart(fig, use_container_width=True)
            elif vis_option == "Cumulative Cash Flow":
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dcf_df["Year"],
                    y=dcf_df["Cumulative CF (€)"],
                    mode="lines+markers",
                    name="Cumulative Cash Flow",
                    line=dict(color="purple")
                ))
                fig.update_layout(
                    title="Cumulative Cash Flow Over Time",
                    xaxis_title="Year",
                    yaxis_title="Cumulative Cash Flow (€)",
                    hovermode="x"
                )
                st.plotly_chart(fig, use_container_width=True)

            # --- New Visualization: Debt Repayment vs. Post-Debt Cash Flow ---
            months = loan_years * 12
            monthly_rate = interest_rate / 100 / 12
            debt_amount = results["debt"]

            # Calculate effective debt payoff period using npf.nper
            amortization_months = npf.nper(monthly_rate, -results["monthly_debt_payment"], debt_amount)
            if amortization_months > months:
                payoff_year_value = None  # Debt not fully repaid within project loan term
                payoff_year_text = "Not repaid within loan term"
            else:
                payoff_year_value = np.ceil(amortization_months / 12)
                payoff_year_text = f"Year {int(payoff_year_value)}"

            # Simulate annual amortization over the loan term (using a monthly loop)
            remaining_principal = debt_amount
            annual_principal_repaid = []
            annual_interest_paid = []
            for year in range(1, loan_years + 1):
                principal_this_year = 0
                interest_this_year = 0
                for m in range(12):
                    if remaining_principal <= 0:
                        break
                    interest_payment = remaining_principal * monthly_rate
                    principal_payment = results["monthly_debt_payment"] - interest_payment
                    # avoid overpayment
                    if principal_payment > remaining_principal:
                        principal_payment = remaining_principal
                    principal_this_year += principal_payment
                    interest_this_year += interest_payment
                    remaining_principal -= principal_payment
                annual_principal_repaid.append(principal_this_year)
                annual_interest_paid.append(interest_this_year)

            # Compute cumulative debt repaid over the loan period
            cumulative_debt_repaid = np.cumsum(annual_principal_repaid)

            # Now, compute cumulative post-debt operating cash flow.
            # For years at or before full debt repayment, assume operating cash is fully used for debt service.
            # After payoff (if achieved), the full operating cash (annual_revenue + annual_opex) becomes available.
            cumulative_post_debt_cf = []
            post_debt_cf_total = 0
            for year in range(1, loan_years + 1):
                if (payoff_year_value is not None) and (year > payoff_year_value):
                    annual_post_debt = annual_revenue + annual_opex  # debt service no longer applies
                else:
                    annual_post_debt = 0
                post_debt_cf_total += annual_post_debt
                cumulative_post_debt_cf.append(post_debt_cf_total)

            # Create a combined chart to visualize both series
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=list(range(1, loan_years + 1)),
                y=cumulative_debt_repaid,
                mode="lines+markers",
                name="Cumulative Debt Repaid",
                line=dict(color="darkblue")
            ))
            fig2.add_trace(go.Scatter(
                x=list(range(1, loan_years + 1)),
                y=cumulative_post_debt_cf,
                mode="lines+markers",
                name="Cumulative Post-Debt Operating Cash Flow",
                line=dict(color="green")
            ))
            fig2.update_layout(
                title="Debt Repayment vs. Post-Debt Operating Cash Flow",
                xaxis_title="Year",
                yaxis_title="Amount (€)",
                hovermode="x unified"
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown(f"**Debt is repaid by:** {payoff_year_text}")

        with tab_lcoe:
            st.header("LCOE Calculation")
            st.markdown("""
            **Levelized Cost of Electricity (LCOE)** is a key metric representing the cost per unit of electricity generated over the system’s lifetime.
            
            The LCOE is calculated as:
            
            **LCOE = (Annualized CAPEX per Outpost + Annual OPEX per Outpost) / Annual Energy Production per Outpost**
            """)
            st.metric("LCOE (€/kWh)", f"{results['lcoe']:.4f}")
            
            r = interest_rate / 100
            n = loan_years
            CRF = (r * (1+r)**n) / ((1+r)**n - 1) if (1+r)**n - 1 != 0 else 0
            total_capex_per_outpost = params["microgrid_capex"] + params["drones_capex"]
            annualized_capex = total_capex_per_outpost * CRF
            annual_opex_per_outpost = results["annual_opex_per_outpost"]
            annual_energy = annual_energy_production
            
            lcoe_breakdown = pd.DataFrame({
                "Metric": ["Annualized CAPEX per Outpost (€/year)", "Annual OPEX per Outpost (€/year)", "Annual Energy Production (kWh/year)"],
                "Value": [annualized_capex, annual_opex_per_outpost, annual_energy]
            })
            st.markdown("**Calculation Breakdown:**")
            st.table(lcoe_breakdown)

            # Calculate diesel generator LCOE
            r = interest_rate / 100
            n = loan_years
            CRF = (r * (1+r)**n) / ((1+r)**n - 1) if (1+r)**n - 1 != 0 else 0

            # Annualized cost components for one diesel generator:
            annualized_capex_diesel = diesel_generator_capex * CRF * number_diesel_generators
            annual_fuel_consumption_diesel = params["genset_fuel_per_hour"] * params["genset_operating_hours"] * operating_days_per_year  # (L/year) per unit
            annual_fuel_cost = annual_fuel_consumption_diesel * diesel_fuel_cost
            diesel_opex_total = diesel_generator_opex
            # Now multiply each by the number of diesel generators:
            total_annualized_capex_diesel = annualized_capex_diesel * number_diesel_generators
            total_diesel_opex = diesel_opex_total * number_diesel_generators        
            total_annual_fuel_cost = annual_fuel_cost * number_diesel_generators
            annual_total_cost_diesel = total_annualized_capex_diesel + total_diesel_opex + total_annual_fuel_cost

            # Estimate annual electricity production from one diesel generator, then multiply:
            annual_electricity_diesel = annual_fuel_consumption_diesel * diesel_generator_efficiency
            annual_electricity_diesel_total = annual_electricity_diesel * number_diesel_generators

            # Diesel LCOE (€/kWh)
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
                    annual_electricity_diesel
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
                        'Absolute_Avoidance_Per_Outpost': '{:.2f}', 
                        'Absolute_Avoidance_All_Outposts': '{:.2f}',
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
                    'Absolute_Avoidance_All_Outposts', 
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

            # NEW: Combined Sensitivity Analysis Graph
            st.markdown("#### Combined Sensitivity Analysis")
            combined_chart = create_combined_sensitivity_graph(
                sensitivity_results,
                sensitivity_param_options[selected_param]
            )
            st.plotly_chart(combined_chart, use_container_width=True)

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
                    'Low_Value': low_result['ghg_abs_avoidance_all_outposts'] - base_avoidance,
                    'High_Value': high_result['ghg_abs_avoidance_all_outposts'] - base_avoidance
                }

            if st.button("Run Multi-Parameter Analysis"):
                tornado_data = []
                base_result = calculate_os4p(params)
                base_avoidance = base_result['ghg_abs_avoidance_all_outposts']
                
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
                        title=f'Tornado Chart: Impact on Absolute GHG Emission Avoidance (±{variation_pct}% variation)',
                        xaxis_title='Change in Absolute GHG Emission Avoidance (tCO₂e/year)',
                        barmode='overlay',
                        legend=dict(
                            orientation="h",
                            y=1.1,
                            x=0.5,
                            xanchor='center'
                        ),
                        margin=dict(l=100)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown(f"""
                    ### Interpretation:
                    - This chart shows how sensitive absolute GHG emission avoidance is to changes in each parameter.
                    - Longer bars indicate parameters with greater impact.
                    - Blue bars show the impact when the parameter increases by {variation_pct}%.
                    - Red bars show the impact when the parameter decreases by {variation_pct}%.
                    """)
                    st.subheader("Parameter Elasticity")
                    st.markdown("""
                    This measures how responsive GHG emission avoidance is to a 1% change in each parameter.
                    Higher absolute values indicate more influential parameters.
                    """)
                    tornado_df['Elasticity'] = (tornado_df['High_Value'] / base_avoidance) / (variation_pct / 100)
                    elasticity_df = tornado_df[['Parameter', 'Elasticity']].sort_values('Elasticity', ascending=False, key=abs)
                    st.dataframe(elasticity_df.style.format({'Elasticity': '{:.3f}'}))
                else:
                    st.warning("Please select at least one parameter group to analyze.")
        
        r = interest_rate / 100
        n = loan_years
        CRF = (r * (1+r)**n) / ((1+r)**n - 1) if (1+r)**n - 1 != 0 else 0
        total_capex_per_outpost = params["microgrid_capex"] + params["drones_capex"]
        annualized_capex = total_capex_per_outpost * CRF
        annual_opex_per_outpost = results["annual_opex_per_outpost"]
        annual_energy = annual_energy_production
        
        lcoe_breakdown = pd.DataFrame({
            "Metric": ["Annualized CAPEX per Outpost (€/year)", "Annual OPEX per Outpost (€/year)", "Annual Energy Production (kWh/year)"],
            "Value": [annualized_capex, annual_opex_per_outpost, annual_energy]
        })
        
        pdf_bytes = generate_pdf(results, params, lcoe_breakdown, dcf_df, npv_value, irr_value, payback)
        st.download_button(label="Download Executive Summary", data=pdf_bytes, file_name="OS4P_Report.pdf", mime="application/pdf")

    if __name__ == "__main__":
        main()
