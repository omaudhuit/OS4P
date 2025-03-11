import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF  # pip install fpdf2

st.set_page_config(page_title="OS4P Green Sentinel", layout="wide")

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

    # CAPEX Inputs
    microgrid_capex = params["microgrid_capex"]
    drones_capex = params["drones_capex"]
    bos_capex = params["bos_capex"]
    
    # OPEX Inputs
    maintenance_opex = params["maintenance_opex"]
    communications_opex = params["communications_opex"]
    security_opex = params["security_opex"]

    # Optional detailed CAPEX components
    detailed_capex = params.get("detailed_capex", None)

    # CO₂ Savings Calculation (Including GENSET)
    genset_fuel_per_hour = 2.5  # Liters per hour (GENSET)
    genset_fuel_per_day = genset_fuel_per_hour * 24
    daily_fuel_consumption = ((large_patrol_fuel + rib_fuel + small_patrol_fuel) * hours_per_day_base) + genset_fuel_per_day
    annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year
    manned_co2_emissions = annual_fuel_consumption * co2_factor
    autonomous_co2_emissions = maintenance_emissions
    co2_savings_per_outpost = (manned_co2_emissions - autonomous_co2_emissions) / 1000
    co2_savings_all_outposts = co2_savings_per_outpost * num_outposts
    co2_savings_lifetime = co2_savings_all_outposts * loan_years

    # Financial Calculations
    total_capex_per_outpost = microgrid_capex + drones_capex + bos_capex
    total_capex = total_capex_per_outpost * num_outposts
    annual_opex_per_outpost = maintenance_opex + communications_opex + security_opex
    annual_opex = annual_opex_per_outpost * num_outposts
    lifetime_opex = annual_opex * loan_years
    
    pilot_markup = total_capex * 1.25
    grant_coverage = 0.60
    total_grant = grant_coverage * pilot_markup
    debt = pilot_markup - total_grant

    monthly_interest_rate = interest_rate / 100 / 12
    num_months = loan_years * 12
    monthly_debt_payment = (debt * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -num_months)
    lifetime_debt_payment = monthly_debt_payment * num_months

    sla_multiplier = 1 + sla_premium / 100
    monthly_fee_unit = ((monthly_debt_payment / num_outposts) + (annual_opex_per_outpost / 12)) * sla_multiplier
    annual_fee_unit = monthly_fee_unit * 12
    lifetime_fee_total = annual_fee_unit * num_outposts * loan_years

    # Cost Efficiency Calculation
    cost_efficiency_per_ton = total_grant / co2_savings_all_outposts if co2_savings_all_outposts > 0 else float('inf')
    cost_efficiency_lifetime = total_grant / co2_savings_lifetime if co2_savings_lifetime > 0 else float('inf')
    
    # Innovation Fund Score calculation
    innovation_fund_score = calculate_innovation_fund_score(cost_efficiency_per_ton)
    innovation_fund_score_lifetime = calculate_innovation_fund_score(cost_efficiency_lifetime)
    
    tco = total_capex + lifetime_opex
    tco_per_outpost = tco / num_outposts

    # LCOE Calculation (€/kWh)
    r = interest_rate / 100  # convert to decimal
    n = loan_years
    if (1+r)**n - 1 != 0:
        CRF = (r * (1+r)**n) / ((1+r)**n - 1)
    else:
        CRF = 0
    annualized_capex = total_capex_per_outpost * CRF
    annual_energy = params["annual_energy_production"]
    lcoe = (annualized_capex + annual_opex_per_outpost) / annual_energy

    # Prepare CAPEX breakdown
    capex_breakdown = {
        "Microgrid": microgrid_capex * num_outposts,
        "Drones": drones_capex * num_outposts,
        "BOS (Balance of System)": bos_capex * num_outposts
    }
    
    # Prepare detailed CAPEX breakdown if available
    detailed_capex_breakdown = None
    if detailed_capex:
        detailed_capex_breakdown = {}
        for category, value in detailed_capex.items():
            detailed_capex_breakdown[category] = value * num_outposts

    result = {
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
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
        "total_grant": total_grant,
        "debt": debt,
        "lifetime_debt_payment": lifetime_debt_payment,
        "lcoe": lcoe,
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
    
    if detailed_capex_breakdown:
        result["detailed_capex_breakdown"] = detailed_capex_breakdown
    
    return result

def create_cost_breakdown_chart(capex_data, opex_data, detailed_capex=None):
    if detailed_capex is not None:
        capex_detailed_df = pd.DataFrame(list(detailed_capex.items()), columns=['Category', 'Value'])
        capex_detailed_df['Type'] = 'CAPEX (Detailed)'
        opex_df = pd.DataFrame(list(opex_data.items()), columns=['Category', 'Value'])
        opex_df['Type'] = 'OPEX (Annual)'
        combined_df = pd.concat([capex_detailed_df, opex_df])
    else:
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

def perform_sensitivity_analysis(base_params, sensitivity_param, range_values):
    results = []
    for value in range_values:
        params = base_params.copy()
        params[sensitivity_param] = value
        result = calculate_os4p(params)
        results.append({
            'Parameter_Value': value,
            'CO2_Savings_Per_Outpost': result['co2_savings_per_outpost'],
            'CO2_Savings_All_Outposts': result['co2_savings_all_outposts'],
            'Manned_CO2_Emissions': result['manned_co2_emissions'] / 1000,
            'Autonomous_CO2_Emissions': result['autonomous_co2_emissions'] / 1000,
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
        if row['CO2_Savings_All_Outposts'] > 0:
            ce_ratio = 500000 / row['CO2_Savings_All_Outposts']
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
        name='CO2 Savings',
        fill='tonexty',
        fillcolor='rgba(0, 255, 0, 0.2)',
        line=dict(width=0)
    ))
    
    fig.update_layout(
        title=f'CO2 Emissions Sensitivity to {param_name}',
        xaxis_title=param_name,
        yaxis_title='CO2 Emissions (tonnes/year)',
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

def generate_pdf(results, params, lcoe_breakdown):
    """
    Generate a PDF report that aggregates key dashboard information.
    Uses a Unicode TrueType font (DejaVu Sans) to support non-Latin1 characters.
    Ensure the fonts folder is at the same level as this .py file,
    and that DejaVuSans.ttf and DejaVuSans-Bold.ttf are inside.
    """
    pdf = FPDF()
    pdf.unifontsubset = False  # Disable font subsetting to avoid issues
    pdf.add_page()

    # Load the regular and bold fonts from the "fonts" folder
    pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "fonts/DejaVuSans-Bold.ttf", uni=True)

    # Use bold font for the header
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "“Green Sentinel” OS4P", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("DejaVu", "", 12)
    intro_text = (
        "The Green Sentinel (OS4P) project in Greece aims to significantly reduce CO₂ emissions through the deployment of Offgrid Smart Surveillance Security Sentinel Pylons (OSPs) and the integration of drones for continuous surveillance."
        "Renewable Energy Generation and CO₂ ReductionEach OSP unit is equipped with a 10 kWp solar photovoltaic system and a 3 kW wind turbine, collectively generating approximately 22,500 kWh of renewable energy annually. This clean energy replaces the need for diesel generators and powers autonomous drone systems that further reduce the dependency on traditional fuel consuming vessels for surveillance purposes."
        "A full summary of the impact is detailed below"
        "As mentioned, Drone Integration for Surveillance and Additional CO₂ Savings A critical component to the solution is the integration of AI-driven drones for 24/7 surveillance, offering a lower carbon footprint compared to more traditional surveillance vehicles (land, sea, air)."
        "Conclusion: By combining renewable energy generation with drone-based surveillance, the Green Sentinel project not only enhances operational efficiency but also aligns with Greece's and the European Union's climate resilience and decarbonization targets, setting a benchmark for sustainable security solutions."
    )
    pdf.multi_cell(0, 10, intro_text)
    
    pdf.ln(5)
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "Overview Metrics", ln=True)
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 10, f"CO₂ Savings per Outpost (tonnes/year): {results['co2_savings_per_outpost']:.1f}", ln=True)
    pdf.cell(0, 10, f"Total CO₂ Savings per Year (tonnes): {results['co2_savings_all_outposts']:.1f}", ln=True)
    pdf.cell(0, 10, f"Lifetime CO₂ Savings (tonnes): {results['co2_savings_lifetime']:.1f}", ln=True)
    pdf.cell(0, 10, f"Cost Efficiency (€/tonne CO₂ avoided): {results['cost_efficiency_per_ton']:.2f}", ln=True)
    
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
    pdf.cell(0, 10, f"Grant Coverage (€): {results['total_grant']:,.0f}", ln=True)
    pdf.cell(0, 10, f"Debt Financing Required (€): {results['debt']:,.0f}", ln=True)
    
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
    
    # Output the PDF as bytes
    pdf_bytes = pdf.output(dest="S").encode("latin1", errors="replace")
    return pdf_bytes

def main():
    st.title("OS4P Green Sentinel")
    st.markdown("### Configure Your OS4P System Below")
    
    with st.sidebar:
        st.header("User Inputs")
        st.subheader("System Configuration")
        num_outposts = st.number_input("Number of Outposts", min_value=1, max_value=1000, value=10, step=1, format="%d")
        
        st.subheader("Fuel Consumption (Liters per Hour)")
        large_patrol_fuel = st.number_input("Large Patrol Boat Fuel", min_value=50, max_value=300, value=150, step=10, format="%d")
        rib_fuel = st.number_input("RIB Boat Fuel", min_value=10, max_value=100, value=50, step=5, format="%d")
        small_patrol_fuel = st.number_input("Small Patrol Boat Fuel", min_value=5, max_value=50, value=30, step=5, format="%d")
        hours_per_day_base = st.number_input("Patrol Hours per Day", min_value=4, max_value=24, value=8, step=1, format="%d")
        
        st.subheader("Financial Parameters")
        interest_rate = st.number_input("Interest Rate (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.1, format="%.1f")
        loan_years = st.number_input("Project Lifetime (years)", min_value=3, max_value=25, value=10, step=1, format="%d")
        sla_premium = st.number_input("SLA Premium (%)", min_value=0.0, max_value=50.0, value=15.0, step=1.0, format="%.1f")
        
        st.subheader("Operational Parameters")
        operating_days_per_year = st.number_input("Operating Days per Year", min_value=200, max_value=365, value=300, step=1, format="%d")
        co2_factor = st.number_input("CO₂ Factor (kg CO₂ per liter)", min_value=0.5, max_value=3.0, value=1.0, step=0.1, format="%.1f")
        maintenance_emissions = st.number_input("Maintenance Emissions (kg CO₂)", min_value=500, max_value=5000, value=1594, step=10, format="%d")
        
        st.subheader("OPEX Inputs (€ per Outpost per Year)")
        maintenance_opex = st.number_input("Maintenance OPEX", min_value=1000, max_value=50000, value=15000, step=1000, format="%d")
        communications_opex = st.number_input("Communications OPEX", min_value=1000, max_value=20000, value=6000, step=1000, format="%d")
        security_opex = st.number_input("Security OPEX", min_value=1000, max_value=30000, value=9000, step=1000, format="%d")
        
        st.subheader("Energy Production")
        annual_energy_production = st.number_input(
            "Annual Energy Production per Outpost (kWh/year)", 
            min_value=1000, 
            max_value=100000, 
            value=15000, 
            step=1000, 
            format="%d"
        )
        
        st.subheader("CAPEX Summary (€ per Outpost)")
        show_capex_detail = st.checkbox("Show detailed CAPEX breakdown", value=False)
        
        if show_capex_detail:
            st.markdown("#### Microgrid CAPEX Breakdown")
            solar_pv_capex = st.number_input("Solar PV System (10kWp)", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
            wind_turbine_capex = st.number_input("Wind Turbine (3kW)", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
            battery_capex = st.number_input("Battery Storage (30kWh)", min_value=10000, max_value=100000, value=36000, step=1000, format="%d")
            telecom_capex = st.number_input("Telecommunications", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
            bos_micro_capex = st.number_input("Microgrid BOS", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
            install_capex = st.number_input("Installation & Commissioning", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
            microgrid_capex = solar_pv_capex + wind_turbine_capex + battery_capex + telecom_capex + bos_micro_capex + install_capex
            st.markdown(f"**Total Microgrid CAPEX: €{microgrid_capex:,}**")
            
            st.markdown("#### Drone System CAPEX Breakdown")
            drone_units = st.number_input("Number of Drones per Outpost", min_value=1, max_value=10, value=3, step=1, format="%d")
            drone_unit_cost = st.number_input("Cost per Drone (€)", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
            drones_capex = drone_units * drone_unit_cost
            st.markdown(f"**Total Drones CAPEX: €{drones_capex:,}**")
            
            st.markdown("#### Other CAPEX")
            bos_capex = st.number_input("Additional BOS CAPEX", min_value=0, max_value=100000, value=40000, step=5000, format="%d")
            total_capex_per_outpost = microgrid_capex + drones_capex + bos_capex
            st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
        else:
            microgrid_capex = st.number_input("Microgrid CAPEX", min_value=50000, max_value=200000, value=110000, step=5000, format="%d")
            drones_capex = st.number_input("Drones CAPEX", min_value=20000, max_value=100000, value=60000, step=5000, format="%d")
            bos_capex = st.number_input("BOS (Balance of System) CAPEX", min_value=10000, max_value=100000, value=40000, step=5000, format="%d")
    
    # Prepare the parameters dict
    params = {
        "num_outposts": num_outposts,
        "large_patrol_fuel": large_patrol_fuel,
        "rib_fuel": rib_fuel,
        "small_patrol_fuel": small_patrol_fuel,
        "hours_per_day_base": hours_per_day_base,
        "interest_rate": interest_rate,
        "loan_years": loan_years,
        "sla_premium": sla_premium,
        "operating_days_per_year": operating_days_per_year,
        "co2_factor": co2_factor,
        "maintenance_emissions": maintenance_emissions,
        "maintenance_opex": maintenance_opex,
        "communications_opex": communications_opex,
        "security_opex": security_opex,
        "annual_energy_production": annual_energy_production
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
            f"Drones ({drone_units}x)": drones_capex,
            "Additional BOS": bos_capex
        }
    else:
        params["microgrid_capex"] = microgrid_capex
        params["drones_capex"] = drones_capex
        params["bos_capex"] = bos_capex
    
    # Calculate results
    results = calculate_os4p(params)
    
    # Tabs
    tab_intro, tab_overview, tab_financial, tab_lcoe, tab_visualizations, tab_sensitivity = st.tabs(
        ["Introduction", "Overview", "Financial Details", "LCOE Calculation", "Visualizations", "Sensitivity Analysis"]
    )
    
    with tab_intro:
        st.header("Introduction")
        st.markdown("""
        ****OS4P Green Sentinel****

        Problem Statement

The European Union faces increasing pressures from climate change and escalating geopolitical challenges, particularly around border security and critical infrastructure resilience. Traditional surveillance methods and power solutions for remote outposts and border checkpoints predominantly rely on diesel generators and manned patrol operations, including diesel-powered vehicles and vessels. These conventional approaches:

 - Contribute significantly to greenhouse gas emissions, exacerbating climate change impacts.

 - Suffer from logistical vulnerabilities, such as fuel supply disruptions in conflict-prone or extreme weather-affected regions.

 - Offer limited resilience, leading to infrastructural vulnerabilities during extreme weather or crises.

 - Lack scalability, hindering expansion and modernization of surveillance and secure communication capabilities.

Consequently, there is an urgent need for integrated, autonomous, and sustainable energy solutions to support border security and enhance civil protection across the EU while aligning with stringent climate and environmental targets.

        Solution: Green Sentinel (OS4P)

The Green Sentinel solution involves deploying autonomous Off-grid Smart Surveillance Security Sentinel Pylons (OS4P), integrating renewable energy generation, energy storage systems, drone-based surveillance, AI-driven monitoring, and secure telecommunications.

Key Components:

Renewable Energy Generation: Each OS4P pylon incorporates a hybrid renewable energy generation system comprising:

 - Solar PV System: A 10 kWp solar photovoltaic installation capable of producing approximately 15,000 kWh annually.

 - Wind Turbine: A complementary 3 kW wind turbine that generates approximately 7,500 kWh per year, bringing total renewable generation per pylon to approximately 22,500 kWh annually.

 - Energy Storage System: Equipped with a robust 30 kWh battery system, each sentinel ensures continuous power supply, resilience during periods of limited renewable generation, and effective load management.

        Drone-Based Autonomous Surveillance

Each OS4P unit integrates AI-driven drones to provide continuous, autonomous surveillance:

Drones: Two QuantumSystems Scorpion drones per pylon, consuming about 1.5 kWh per patrol cycle (totaling ~144 kWh/day for continuous operation).

AI-Powered Analytics: Real-time threat detection, surveillance analytics, and automated monitoring through integrated high-resolution cameras, radar, and edge computing capabilities.

        Technical Integration and Communication:

Each OS4P unit integrates advanced telecommunications infrastructure:

 - Secure Communications: Utilizing 5G, Starlink satellite services, and secure LINK-16 communications, ensuring robust real-time data transfer and connectivity.

 - Structural Design: Robust tower structure suitable for harsh environments, ensuring resilience against extreme weather and operational disruptions.

        Environmental Impact

The Green Sentinel project offers significant environmental and climate benefits:

 - CO₂ Emission Reductions: Each OS4P unit prevents between 18 to 30 metric tons of CO₂ emissions annually by replacing diesel-generated power. Over 10 years, the total CO₂ avoided by 45 units is projected between 8,100 to 13,500 metric tons.

 - Additional CO₂ Savings: By replacing diesel-powered patrol vessels and vehicles, the cumulative 10-year CO₂ savings across a broader deployment (e.g., 200 units) could exceed 60 million kilograms.

        Operational and Socio-Economic Advantages

 - Security Enhancement: Continuous, automated surveillance improves response time and situational awareness, significantly enhancing border and infrastructure security.

 - Job Creation: Local jobs in installation, operation, and ongoing maintenance.

 - Innovation Leadership: Demonstrates a scalable, sustainable, and replicable model aligning with the EU’s Green Deal and security frameworks.

In summary, Green Sentinel (OS4P) addresses critical EU security and climate resilience challenges by integrating renewable energy and autonomous surveillance, setting a new standard for sustainable, resilient, and efficient border security and critical infrastructure protection.

        """)
    
    with tab_overview:
        st.subheader("Environmental Impact")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("CO₂ Savings per Outpost (tonnes/year)", f"{results['co2_savings_per_outpost']:.1f}")
        with col2:
            st.metric("Total CO₂ Savings per Year (tonnes)", f"{results['co2_savings_all_outposts']:.1f}")
        with col3:
            st.metric("Lifetime CO₂ Savings (tonnes)", f"{results['co2_savings_lifetime']:.1f}")
        
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
    
    with tab_financial:
        st.subheader("Financing Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Pilot Cost with Markup (€)", f"{results['pilot_markup']:,.0f}")
            st.metric("Grant Coverage (€)", f"{results['total_grant']:,.0f}")
            st.metric("Debt Financing Required (€)", f"{results['debt']:,.0f}")
        with col2:
            st.metric("Monthly Debt Payment (€)", f"{results['monthly_debt_payment']:,.0f}")
            st.metric("Lifetime Debt Payment (€)", f"{results['lifetime_debt_payment']:,.0f}")
        with col3:
            st.metric("Monthly Fee per Outpost (€)", f"{results['monthly_fee_unit']:,.0f}")
            st.metric("Annual Fee per Outpost (€)", f"{results['annual_fee_unit']:,.0f}")
            st.metric("Lifetime Total Fee (€)", f"{results['lifetime_fee_total']:,.0f}")
        
        st.subheader("CAPEX Breakdown")
        if "detailed_capex_breakdown" in results:
            detailed_capex_df = pd.DataFrame.from_dict(results["detailed_capex_breakdown"], orient='index', columns=["Amount (€)"])
            detailed_capex_df["Percentage"] = (detailed_capex_df["Amount (€)"] / detailed_capex_df["Amount (€)"].sum() * 100).round(1).astype(str) + '%'
            st.dataframe(detailed_capex_df)
            st.markdown("**Detailed CAPEX Breakdown**")
        else:
            capex_df = pd.DataFrame.from_dict(results["capex_breakdown"], orient='index', columns=["Amount (€)"])
            capex_df["Percentage"] = (capex_df["Amount (€)"] / capex_df["Amount (€)"].sum() * 100).round(1).astype(str) + '%'
            st.dataframe(capex_df)
        
        st.subheader("Annual OPEX Breakdown")
        opex_df = pd.DataFrame.from_dict(results["opex_breakdown"], orient='index', columns=["Amount (€)"])
        opex_df["Percentage"] = (opex_df["Amount (€)"] / opex_df["Amount (€)"].sum() * 100).round(1).astype(str) + '%'
        st.dataframe(opex_df)
    
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
        total_capex_per_outpost = params["microgrid_capex"] + params["drones_capex"] + params["bos_capex"]
        annualized_capex = total_capex_per_outpost * CRF
        annual_opex_per_outpost = results["annual_opex_per_outpost"]
        annual_energy = annual_energy_production
        
        lcoe_breakdown = pd.DataFrame({
            "Metric": ["Annualized CAPEX per Outpost (€/year)", "Annual OPEX per Outpost (€/year)", "Annual Energy Production (kWh/year)"],
            "Value": [annualized_capex, annual_opex_per_outpost, annual_energy]
        })
        st.markdown("**Calculation Breakdown:**")
        st.table(lcoe_breakdown)
    
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
    
    with tab_sensitivity:
        st.subheader("CO₂ Emissions Sensitivity Analysis")
        st.markdown("Select a parameter to analyze its impact on CO₂ emissions:")
        
        sensitivity_param_options = {
            "large_patrol_fuel": "Large Patrol Boat Fuel (L/h)",
            "rib_fuel": "RIB Boat Fuel (L/h)",
            "small_patrol_fuel": "Small Patrol Boat Fuel (L/h)",
            "hours_per_day_base": "Patrol Hours per Day",
            "operating_days_per_year": "Operating Days per Year",
            "co2_factor": "CO₂ Factor (kg CO₂/L)",
            "maintenance_emissions": "Maintenance Emissions (kg CO₂)"
        }
        
        col1, col2 = st.columns([2, 3])
        with col1:
            selected_param = st.selectbox(
                "Parameter to analyze:", 
                list(sensitivity_param_options.keys()),
                format_func=lambda x: sensitivity_param_options[x]
            )
            if selected_param == "large_patrol_fuel":
                min_val, max_val, default_val, step = 50, 300, params[selected_param], 25
            elif selected_param == "rib_fuel":
                min_val, max_val, default_val, step = 10, 100, params[selected_param], 10
            elif selected_param == "small_patrol_fuel":
                min_val, max_val, default_val, step = 5, 50, params[selected_param], 5
            elif selected_param == "hours_per_day_base":
                min_val, max_val, default_val, step = 4, 24, params[selected_param], 2
            elif selected_param == "operating_days_per_year":
                min_val, max_val, default_val, step = 200, 365, params[selected_param], 20
            elif selected_param == "co2_factor":
                min_val, max_val, default_val, step = 0.5, 3.0, params[selected_param], 0.25
            elif selected_param == "maintenance_emissions":
                min_val, max_val, default_val, step = 500, 5000, params[selected_param], 500
            
            min_range = st.number_input("Minimum value:", value=min_val, step=step)
            max_range = st.number_input("Maximum value:", value=max_val, step=step)
            num_steps = st.number_input("Number of data points:", value=10, min_value=5, max_value=20, step=1)
        
        with col2:
            if min_range >= max_range:
                st.error("Minimum value must be less than maximum value!")
            else:
                if selected_param == "co2_factor":
                    range_values = np.linspace(min_range, max_range, int(num_steps))
                else:
                    range_values = np.linspace(min_range, max_range, int(num_steps))
                    if selected_param in ["hours_per_day_base", "operating_days_per_year"]:
                        range_values = range_values.astype(int)
                sensitivity_results = perform_sensitivity_analysis(params, selected_param, range_values)
                st.markdown("#### Sensitivity Analysis Results:")
                st.dataframe(sensitivity_results.style.format({
                    'Parameter_Value': '{:.2f}' if selected_param == "co2_factor" else '{:.0f}',
                    'CO2_Savings_Per_Outpost': '{:.2f}', 
                    'CO2_Savings_All_Outposts': '{:.2f}',
                    'Manned_CO2_Emissions': '{:.2f}',
                    'Autonomous_CO2_Emissions': '{:.2f}'
                }))
        
        st.markdown("#### Sensitivity Analysis Visualizations")
        col1, col2 = st.columns(2)
        with col1:
            co2_savings_chart = create_sensitivity_chart(
                sensitivity_results, 
                sensitivity_param_options[selected_param],
                'CO2_Savings_All_Outposts', 
                'Total CO₂ Savings (tonnes/year)'
            )
            st.plotly_chart(co2_savings_chart, use_container_width=True)
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
        st.markdown("""
        This chart shows how the Innovation Fund score changes with the parameter value. 
        Higher scores (closer to 12) improve chances of funding. Scores are calculated based on the 
        cost efficiency ratio (EUR/tonne CO₂ saved) using the formula:
        
        **Score = 12 - (12 × cost efficiency ratio / 2000)** when ratio ≤ 2000 EUR/t, **0** otherwise.
        """)
        
        st.subheader("Multi-Parameter Impact Analysis")
        st.markdown("Analyze the impact of multiple parameters simultaneously:")
        col1, col2, col3 = st.columns(3)
        with col1:
            analyze_patrol_fuel = st.checkbox("Patrol Boat Fuel Consumption", value=True)
        with col2:
            analyze_operations = st.checkbox("Operational Parameters", value=True) 
        with col3:
            analyze_emissions = st.checkbox("Emissions Parameters", value=True)
        
        variation_pct = st.slider("Parameter Variation (%)", min_value=5, max_value=50, value=20, step=5,
                              help="How much each parameter will be varied up and down from the base case")
        
        if st.button("Run Multi-Parameter Analysis"):
            tornado_data = []
            base_result = calculate_os4p(params)
            base_savings = base_result['co2_savings_all_outposts']
            
            if analyze_patrol_fuel:
                params_high = params.copy()
                params_high['large_patrol_fuel'] = params['large_patrol_fuel'] * (1 + variation_pct/100)
                high_result = calculate_os4p(params_high)
                params_low = params.copy()
                params_low['large_patrol_fuel'] = params['large_patrol_fuel'] * (1 - variation_pct/100)
                low_result = calculate_os4p(params_low)
                tornado_data.append({
                    'Parameter': 'Large Patrol Fuel',
                    'Low_Value': low_result['co2_savings_all_outposts'] - base_savings,
                    'High_Value': high_result['co2_savings_all_outposts'] - base_savings
                })
                params_high = params.copy()
                params_high['rib_fuel'] = params['rib_fuel'] * (1 + variation_pct/100)
                high_result = calculate_os4p(params_high)
                params_low = params.copy()
                params_low['rib_fuel'] = params['rib_fuel'] * (1 - variation_pct/100)
                low_result = calculate_os4p(params_low)
                tornado_data.append({
                    'Parameter': 'RIB Fuel',
                    'Low_Value': low_result['co2_savings_all_outposts'] - base_savings,
                    'High_Value': high_result['co2_savings_all_outposts'] - base_savings
                })
            
            if analyze_operations:
                params_high = params.copy()
                params_high['operating_days_per_year'] = min(365, int(params['operating_days_per_year'] * (1 + variation_pct/100)))
                high_result = calculate_os4p(params_high)
                params_low = params.copy()
                params_low['operating_days_per_year'] = max(200, int(params['operating_days_per_year'] * (1 - variation_pct/100)))
                low_result = calculate_os4p(params_low)
                tornado_data.append({
                    'Parameter': 'Operating Days',
                    'Low_Value': low_result['co2_savings_all_outposts'] - base_savings,
                    'High_Value': high_result['co2_savings_all_outposts'] - base_savings
                })
                params_high = params.copy()
                params_high['hours_per_day_base'] = min(24, int(params['hours_per_day_base'] * (1 + variation_pct/100)))
                high_result = calculate_os4p(params_high)
                params_low = params.copy()
                params_low['hours_per_day_base'] = max(4, int(params['hours_per_day_base'] * (1 - variation_pct/100)))
                low_result = calculate_os4p(params_low)
                tornado_data.append({
                    'Parameter': 'Hours per Day',
                    'Low_Value': low_result['co2_savings_all_outposts'] - base_savings,
                    'High_Value': high_result['co2_savings_all_outposts'] - base_savings
                })
            
            if analyze_emissions:
                params_high = params.copy()
                params_high['co2_factor'] = params['co2_factor'] * (1 + variation_pct/100)
                high_result = calculate_os4p(params_high)
                params_low = params.copy()
                params_low['co2_factor'] = params['co2_factor'] * (1 - variation_pct/100)
                low_result = calculate_os4p(params_low)
                tornado_data.append({
                    'Parameter': 'CO₂ Factor',
                    'Low_Value': low_result['co2_savings_all_outposts'] - base_savings,
                    'High_Value': high_result['co2_savings_all_outposts'] - base_savings
                })
                params_high = params.copy()
                params_high['maintenance_emissions'] = params['maintenance_emissions'] * (1 + variation_pct/100)
                high_result = calculate_os4p(params_high)
                params_low = params.copy()
                params_low['maintenance_emissions'] = params['maintenance_emissions'] * (1 - variation_pct/100)
                low_result = calculate_os4p(params_low)
                tornado_data.append({
                    'Parameter': 'Maintenance Emissions',
                    'Low_Value': low_result['co2_savings_all_outposts'] - base_savings,
                    'High_Value': high_result['co2_savings_all_outposts'] - base_savings
                })
            
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
                    title='Tornado Chart: Impact on CO₂ Savings (±{0}% parameter variation)'.format(variation_pct),
                    xaxis_title='Change in CO₂ Savings (tonnes/year)',
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
                - This chart shows how sensitive CO₂ savings are to changes in each parameter.
                - Longer bars indicate parameters with greater impact.
                - Blue bars show impact when the parameter increases by {variation_pct}%.
                - Red bars show impact when the parameter decreases by {variation_pct}%.
                """)
                st.subheader("Parameter Elasticity")
                st.markdown("""
                This measures how responsive CO₂ savings are to a 1% change in each parameter.
                Higher absolute values indicate more influential parameters.
                """)
                tornado_df['Elasticity'] = (tornado_df['High_Value'] / base_savings) / (variation_pct/100)
                elasticity_df = tornado_df[['Parameter', 'Elasticity']].sort_values('Elasticity', ascending=False, key=abs)
                st.dataframe(elasticity_df.style.format({'Elasticity': '{:.3f}'}))
            else:
                st.warning("Please select at least one parameter group to analyze.")
    
    # Generate PDF
    r = interest_rate / 100
    n = loan_years
    CRF = (r * (1+r)**n) / ((1+r)**n - 1) if (1+r)**n - 1 != 0 else 0
    total_capex_per_outpost = params["microgrid_capex"] + params["drones_capex"] + params["bos_capex"]
    annualized_capex = total_capex_per_outpost * CRF
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
