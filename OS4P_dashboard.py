import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="OS4P Interactive Dashboard", layout="wide")

def calculate_innovation_fund_score(cost_efficiency_ratio):
    """
    Calculate Innovation Fund score based on cost efficiency ratio
    
    For INNOVFUND-2024-NZT-PILOTS topic:
    - If cost efficiency ratio is <= 2000 EUR/t CO2-eq: 12 - (12 x (ratio / 2000))
    - If cost efficiency ratio is > 2000 EUR/t CO2-eq: 0 points
    
    Returns rounded to nearest half point, min 0, max 12
    """
    if cost_efficiency_ratio <= 2000:
        score = 12 - (12 * (cost_efficiency_ratio / 2000))
        # Round to nearest half point
        score = round(score * 2) / 2
        return max(0, score)
    else:
        return 0

def calculate_lcoe(params):
    """
    Calculate the Levelized Cost of Energy (LCOE) for the OS4P microgrid system
    
    LCOE = (Sum of costs over lifetime) / (Sum of energy produced over lifetime)
    """
    # Extract parameters
    microgrid_capex = params["microgrid_capex"]
    maintenance_opex = params["maintenance_opex"]
    loan_years = params["loan_years"]
    discount_rate = params["interest_rate"]  # Use the same interest rate for consistency
    annual_energy_production = params["annual_energy_production"]
    degradation_rate = params.get("degradation_rate", 0.5) / 100  # Convert percentage to decimal
    
    # Initialize arrays for calculations
    years = np.arange(1, loan_years + 1)
    costs = np.zeros(loan_years)
    energy = np.zeros(loan_years)
    
    # Populate arrays for each year
    for i, year in enumerate(years):
        # Costs: CAPEX in year 1, OPEX in all years
        if i == 0:
            costs[i] = microgrid_capex + maintenance_opex
        else:
            costs[i] = maintenance_opex
        
        # Energy production with annual degradation
        energy[i] = annual_energy_production * (1 - degradation_rate) ** (i)
        
        # Apply discount factor to both costs and energy
        discount_factor = 1 / (1 + discount_rate / 100) ** i
        costs[i] *= discount_factor
        energy[i] *= discount_factor
    
    # Calculate LCOE
    total_costs = np.sum(costs)
    total_energy = np.sum(energy)
    
    lcoe = total_costs / total_energy if total_energy > 0 else float('inf')
    
    return {
        "lcoe": lcoe,
        "total_costs": total_costs,
        "total_energy": total_energy,
        "yearly_costs": costs,
        "yearly_energy": energy,
        "years": years
    }

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

    # Energy production
    annual_energy_production = params.get("annual_energy_production", 22500)

    # ✅ CO₂ Savings Calculation (Including GENSET)
    genset_fuel_per_hour = 2.5  # Liters per hour (GENSET)
    genset_fuel_per_day = genset_fuel_per_hour * 24  # 24-hour consumption

    daily_fuel_consumption = ((large_patrol_fuel + rib_fuel + small_patrol_fuel) * hours_per_day_base) + genset_fuel_per_day
    annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year
    manned_co2_emissions = annual_fuel_consumption * co2_factor
    autonomous_co2_emissions = maintenance_emissions
    co2_savings_per_outpost = (manned_co2_emissions - autonomous_co2_emissions) / 1000
    co2_savings_all_outposts = co2_savings_per_outpost * num_outposts
    co2_savings_lifetime = co2_savings_all_outposts * loan_years

    # Financial Calculations
    # Total CAPEX calculation
    total_capex_per_outpost = microgrid_capex + drones_capex + bos_capex
    total_capex = total_capex_per_outpost * num_outposts
    
    # Total annual OPEX calculation
    annual_opex_per_outpost = maintenance_opex + communications_opex + security_opex
    annual_opex = annual_opex_per_outpost * num_outposts
    lifetime_opex = annual_opex * loan_years
    
    # Initial project cost calculation
    pilot_markup = total_capex * 1.25
    grant_coverage = 0.60
    total_grant = grant_coverage * pilot_markup
    debt = pilot_markup - total_grant

    # Loan Calculation for CAPEX
    monthly_interest_rate = interest_rate / 100 / 12
    num_months = loan_years * 12
    monthly_debt_payment = (debt * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -num_months)
    lifetime_debt_payment = monthly_debt_payment * num_months

    # SLA Premium
    sla_multiplier = 1 + sla_premium / 100
    monthly_fee_unit = ((monthly_debt_payment / num_outposts) + (annual_opex_per_outpost / 12)) * sla_multiplier
    annual_fee_unit = monthly_fee_unit * 12
    lifetime_fee_total = annual_fee_unit * num_outposts * loan_years

    # ✅ Cost Efficiency Calculation
    cost_efficiency_per_ton = total_grant / co2_savings_all_outposts if co2_savings_all_outposts > 0 else float('inf')
    cost_efficiency_lifetime = total_grant / co2_savings_lifetime if co2_savings_lifetime > 0 else float('inf')
    
    # Innovation Fund Score calculation
    innovation_fund_score = calculate_innovation_fund_score(cost_efficiency_per_ton)
    innovation_fund_score_lifetime = calculate_innovation_fund_score(cost_efficiency_lifetime)
    
    # Total Cost of Ownership (TCO)
    tco = total_capex + lifetime_opex
    tco_per_outpost = tco / num_outposts

    # Calculate LCOE
    lcoe_params = {
        "microgrid_capex": microgrid_capex,
        "maintenance_opex": maintenance_opex,
        "loan_years": loan_years,
        "interest_rate": interest_rate,
        "annual_energy_production": annual_energy_production,
        "degradation_rate": params.get("degradation_rate", 0.5)
    }
    lcoe_results = calculate_lcoe(lcoe_params)

    # Prepare standard CAPEX breakdown
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
        # CO2 Metrics
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
        "daily_fuel_consumption": daily_fuel_consumption,
        "manned_co2_emissions": manned_co2_emissions,
        "autonomous_co2_emissions": autonomous_co2_emissions,
        
        # Financial Metrics
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
        
        # Efficiency Metrics
        "cost_efficiency_per_ton": cost_efficiency_per_ton,
        "cost_efficiency_lifetime": cost_efficiency_lifetime,
        "innovation_fund_score": innovation_fund_score,
        "innovation_fund_score_lifetime": innovation_fund_score_lifetime,
        
        # Energy Metrics
        "annual_energy_production": annual_energy_production,
        "lcoe": lcoe_results["lcoe"],
        "lcoe_total_costs": lcoe_results["total_costs"],
        "lcoe_total_energy": lcoe_results["total_energy"],
        "lcoe_yearly_costs": lcoe_results["yearly_costs"],
        "lcoe_yearly_energy": lcoe_results["yearly_energy"],
        "lcoe_years": lcoe_results["years"],
        
        # Project Financing 
        "pilot_markup": pilot_markup,
        "total_grant": total_grant,
        "debt": debt,
        "lifetime_debt_payment": lifetime_debt_payment,
        
        # Breakdowns for visualizations
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
    
    # Add detailed CAPEX breakdown if available
    if detailed_capex_breakdown:
        result["detailed_capex_breakdown"] = detailed_capex_breakdown
    
    return result

def create_cost_breakdown_chart(capex_data, opex_data, detailed_capex=None):
    if detailed_capex is not None:
        # Create detailed CAPEX breakdown
        capex_detailed_df = pd.DataFrame(list(detailed_capex.items()), columns=['Category', 'Value'])
        capex_detailed_df['Type'] = 'CAPEX (Detailed)'
        
        # Create OPEX breakdown
        opex_df = pd.DataFrame(list(opex_data.items()), columns=['Category', 'Value'])
        opex_df['Type'] = 'OPEX (Annual)'
        
        # Combine dataframes
        combined_df = pd.concat([capex_detailed_df, opex_df])
    else:
        # Use simple CAPEX breakdown
        capex_df = pd.DataFrame(list(capex_data.items()), columns=['Category', 'Value'])
        capex_df['Type'] = 'CAPEX'
        
        # Create OPEX breakdown
        opex_df = pd.DataFrame(list(opex_data.items()), columns=['Category', 'Value'])
        opex_df['Type'] = 'OPEX (Annual)'
        
        # Combine dataframes
        combined_df = pd.concat([capex_df, opex_df])
    
    fig = px.bar(combined_df, x='Category', y='Value', color='Type', 
                 title='Cost Breakdown', 
                 labels={'Value': 'Cost (€)', 'Category': ''})
    
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
    
    # Calculate and display the savings as text on the chart
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

def create_lcoe_comparison_chart(lcoe_value, comparison_sources):
    """
    Create a bar chart comparing OS4P LCOE with other energy sources
    """
    # Add OS4P to the comparison sources
    sources = ["OS4P"] + list(comparison_sources.keys())
    values = [lcoe_value] + list(comparison_sources.values())
    
    # Create color scheme (highlight OS4P)
    colors = ['#ff9999'] + ['#66b3ff'] * len(comparison_sources)
    
    fig = go.Figure(data=[go.Bar(
        x=sources,
        y=values,
        marker_color=colors
    )])
    
    fig.update_layout(
        title_text='LCOE Comparison with Conventional Energy Sources',
        yaxis_title='LCOE (€/kWh)',
        xaxis_title='Energy Source'
    )
    
    return fig

def create_yearly_cash_flow_chart(years, costs, energy, lcoe):
    """
    Create a combined chart showing yearly costs, energy production, and cumulative cash flow
    """
    fig = go.Figure()
    
    # Add yearly costs bars
    fig.add_trace(go.Bar(
        x=years,
        y=costs,
        name='Annual Costs (€)',
        marker_color='#ff9999'
    ))
    
    # Add yearly energy production bars
    fig.add_trace(go.Bar(
        x=years,
        y=energy,
        name='Energy Production (kWh)',
        marker_color='#66b3ff',
        yaxis='y2'
    ))
    
    # Calculate and add cumulative cash flow line
    energy_value = energy * lcoe
    cumulative_cash_flow = np.cumsum(energy_value - costs)
    
    fig.add_trace(go.Scatter(
        x=years,
        y=cumulative_cash_flow,
        name='Cumulative Cash Flow (€)',
        line=dict(width=3, color='green'),
        yaxis='y3'
    ))
    
    # Update layout for three y-axes
    fig.update_layout(
        title_text='Yearly Cash Flow and Energy Production',
        yaxis=dict(title='Annual Costs (€)', side='left'),
        yaxis2=dict(title='Energy Production (kWh)', overlaying='y', side='right'),
        yaxis3=dict(title='Cumulative Cash Flow (€)', overlaying='y', anchor='free', side='right', position=0.95),
        barmode='group',
        legend=dict(x=0.01, y=0.99)
    )
    
    return fig

def perform_sensitivity_analysis(base_params, sensitivity_param, range_values):
    """
    Perform sensitivity analysis by varying one parameter and keeping others constant
    """
    results = []
    
    for value in range_values:
        # Create a copy of the base parameters
        params = base_params.copy()
        # Update the parameter to analyze
        params[sensitivity_param] = value
        # Calculate results with the new parameter value
        result = calculate_os4p(params)
        # Store the parameter value and corresponding results
        results.append({
            'Parameter_Value': value,
            'CO2_Savings_Per_Outpost': result['co2_savings_per_outpost'],
            'CO2_Savings_All_Outposts': result['co2_savings_all_outposts'],
            'Manned_CO2_Emissions': result['manned_co2_emissions'] / 1000,  # Convert to tonnes
            'Autonomous_CO2_Emissions': result['autonomous_co2_emissions'] / 1000,  # Convert to tonnes
            'Cost_Efficiency': result['cost_efficiency_per_ton'],
            'Innovation_Fund_Score': result['innovation_fund_score'],
            'LCOE': result['lcoe']
        })
    
    return pd.DataFrame(results)

def create_sensitivity_chart(sensitivity_data, param_name, y_column, y_label):
    """
    Create a line chart for sensitivity analysis results
    """
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
    """
    Create a chart showing how Innovation Fund score changes with parameter values
    """
    fig = px.line(
        sensitivity_data,
        x='Parameter_Value',
        y='Innovation_Fund_Score',
        markers=True,
        title=f'Innovation Fund Score Sensitivity to {param_name}',
        labels={'Parameter_Value': param_name, 'Innovation_Fund_Score': 'Innovation Fund Score (0-12)'}
    )
    
    # Add reference lines for score thresholds
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

def create_lcoe_sensitivity_chart(sensitivity_data, param_name):
    """
    Create a chart showing how LCOE changes with parameter values
    """
    fig = px.line(
        sensitivity_data,
        x='Parameter_Value',
        y='LCOE',
        markers=True,
        title=f'LCOE Sensitivity to {param_name}',
        labels={'Parameter_Value': param_name, 'LCOE': 'LCOE (€/kWh)'}
    )
    
    # Add reference lines for common energy source costs
    fig.add_hline(y=0.25, line_dash="dash", line_color="red", annotation_text="Diesel Generator (0.25 €/kWh)", 
                 annotation_position="top right")
    fig.add_hline(y=0.15, line_dash="dash", line_color="orange", annotation_text="Grid Electricity (0.15 €/kWh)", 
                 annotation_position="top right")
    fig.add_hline(y=0.05, line_dash="dash", line_color="green", annotation_text="Utility-Scale Renewables (0.05 €/kWh)", 
                 annotation_position="top right")
    
    fig.update_layout(
        xaxis_title=param_name,
        yaxis_title='LCOE (€/kWh)',
        hovermode="x unified"
    )
    
    return fig

def create_emissions_sensitivity_chart(sensitivity_data, param_name):
    """
    Create a dual line chart showing both manned and autonomous emissions
    """
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
    
    # Add CO2 savings as a filled area
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

def main():
    st.title("OS4P Interactive Dashboard")
    
    st.markdown("### Configure Your OS4P System Below")
    
    # User Input Fields
    with st.sidebar:
        st.header("User Inputs")

        st.subheader("System Configuration")
        num_outposts = st.number_input("Number of Outposts", min_value=1, max_value=200, value=10, step=1, format="%d")
        
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

        # Energy production parameters
        st.subheader("Energy Production")
        annual_energy_production = st.number_input("Annual Energy Production (kWh)", min_value=5000, max_value=50000, value=22500, step=500, format="%d")
        degradation_rate = st.number_input("Annual System Degradation (%)", min_value=0.0, max_value=5.0, value=0.5, step=0.1, format="%.1f")

        # Main CAPEX inputs
        st.subheader("CAPEX Summary (€ per Outpost)")
        
        # CAPEX Detailed Breakdown toggle
        show_capex_detail = st.checkbox("Show detailed CAPEX breakdown", value=False)
        
        if show_capex_detail:
            st.markdown("#### Microgrid CAPEX Breakdown")
            solar_pv_capex = st.number_input("Solar PV System (10kWp)", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
            wind_turbine_capex = st.number_input("Wind Turbine (3kW)", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
            battery_capex = st.number_input("Battery Storage (30kWh)", min_value=10000, max_value=100000, value=36000, step=1000, format="%d")
            telecom_capex = st.number_input("Telecommunications", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
            bos_micro_capex = st.number_input("Microgrid BOS", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
            install_capex = st.number_input("Installation & Commissioning", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
            
            # Calculate total microgrid CAPEX from components
            microgrid_capex = solar_pv_capex + wind_turbine_capex + battery_capex + telecom_capex + bos_micro_capex + install_capex
            st.markdown(f"**Total Microgrid CAPEX: €{microgrid_capex:,}**")
            
            st.markdown("#### Drone System CAPEX Breakdown")
            drone_units = st.number_input("Number of Drones per Outpost", min_value=1, max_value=10, value=3, step=1, format="%d")
            drone_unit_cost = st.number_input("Cost per Drone (€)", min_value=5000, max_value=50000, value=20000, step=1000, format="%d")
            
            # Calculate total drone CAPEX
            drones_capex = drone_units * drone_unit_cost
            st.markdown(f"**Total Drones CAPEX: €{drones_capex:,}**")
            
            st.markdown("#### Other CAPEX")
            bos_capex = st.number_input("Additional BOS CAPEX", min_value=0, max_value=100000, value=40000, step=5000, format="%d")
            
            # Show total CAPEX
            total_capex_per_outpost = microgrid_capex + drones_capex + bos_capex
            st.markdown(f"**Total CAPEX per Outpost: €{total_capex_per_outpost:,}**")
        else:
            # Simple CAPEX inputs without breakdown
            microgrid_capex = st.number_input("Microgrid CAPEX", min_value=50000, max_value=200000, value=110000, step=5000, format="%d")
            drones_capex = st.number_input("Drones CAPEX", min_value=20000, max_value=100000, value=60000, step=5000, format="%d")
            bos_capex = st.number_input("BOS (Balance of System) CAPEX", min_value=10000, max_value=100000, value=40000, step=5000, format="%d")
        
        st.subheader("OPEX Inputs (€ per Outpost per Year)")
        maintenance_opex = st.number_input("Maintenance OPEX", min_value=1000, max_value=50000, value=15000, step=1000, format="%d")
        communications_opex = st.number_input("Communications OPEX", min_value=1000, max_value=20000, value=6000, step=1000, format="%d")
        security_opex = st.number_input("Security OPEX", min_value=1000, max_value=30000, value=9000, step=1000, format="%d")

    # Store user inputs in a params dictionary
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
        "annual_energy_production": annual_energy_production,
        "degradation_rate": degradation_rate,
        "maintenance_opex": maintenance_opex,
        "communications_opex": communications_opex,
        "security_opex": security_opex
    }
    
    # Add CAPEX parameters based on whether detailed breakdown is used
    if show_capex_detail:
        params["microgrid_capex"] = microgrid_capex
        params["drones_capex"] = drones_capex
        params["bos_capex"] = bos_capex
        
        # Add detailed CAPEX breakdown
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