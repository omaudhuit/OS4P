# Add energy parameters to the params dictionary
    params["energy_params"] = {
        "solar_capacity_kw": solar_capacity_kw,
        "wind_capacity_kw": wind_capacity_kw,
        "solar_capacity_factor": solar_capacity_factor,
        "wind_capacity_factor": wind_capacity_factor,
        "energy_degradation_rate": energy_degradation_rate
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
    
    # Calculate results
    results = calculate_os4p(params)

    # Display comprehensive results in the main area
    st.header("Base Case Results")
    
    # Create tabs for organized display
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Financial Details", "Visualizations", "Sensitivity Analysis"])import streamlit as st
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

def calculate_lcoe(capital_costs, annual_maintenance, system_lifetime, 
                   annual_energy_production, discount_rate, degradation_rate=0.005):
    """
    Calculate the Levelized Cost of Energy (LCOE)
    
    Parameters:
    -----------
    capital_costs: float
        Total capital costs (CAPEX) in EUR
    annual_maintenance: float
        Annual maintenance and operations costs (OPEX) in EUR
    system_lifetime: int
        System lifetime in years
    annual_energy_production: float
        Annual energy production in kWh (first year)
    discount_rate: float
        Discount rate as a decimal (e.g., 0.05 for 5%)
    degradation_rate: float, optional
        Annual degradation rate of energy production (default: 0.5% per year)
        
    Returns:
    --------
    float: LCOE in EUR/kWh
    """
    # Initialize variables
    total_discounted_costs = capital_costs  # Initial capital costs
    total_discounted_energy = 0
    
    # Calculate discounted costs and energy for each year
    for year in range(1, system_lifetime + 1):
        # Discount factor for this year
        discount_factor = (1 + discount_rate) ** year
        
        # Add discounted annual maintenance costs
        total_discounted_costs += annual_maintenance / discount_factor
        
        # Calculate energy production for this year (accounting for degradation)
        year_energy = annual_energy_production * ((1 - degradation_rate) ** (year - 1))
        
        # Add discounted annual energy production
        total_discounted_energy += year_energy / discount_factor
    
    # Calculate LCOE
    if total_discounted_energy > 0:
        lcoe = total_discounted_costs / total_discounted_energy
        return lcoe
    else:
        return float('inf')  # Return infinity if no energy is produced

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

    # Extract energy parameters required for LCOE calculation
    energy_params = params.get("energy_params", {})
    solar_capacity_kw = energy_params.get("solar_capacity_kw", 10)
    wind_capacity_kw = energy_params.get("wind_capacity_kw", 3)
    solar_capacity_factor = energy_params.get("solar_capacity_factor", 0.15)  # 15% capacity factor
    wind_capacity_factor = energy_params.get("wind_capacity_factor", 0.25)  # 25% capacity factor
    energy_degradation_rate = energy_params.get("energy_degradation_rate", 0.005)  # 0.5% per year
    
    # Calculate annual energy production
    hours_per_year = 365 * 24
    solar_annual_energy = solar_capacity_kw * solar_capacity_factor * hours_per_year  # kWh
    wind_annual_energy = wind_capacity_kw * wind_capacity_factor * hours_per_year  # kWh
    total_annual_energy = solar_annual_energy + wind_annual_energy  # kWh
    
    # Capital costs for energy system (using microgrid costs)
    energy_capital_costs = microgrid_capex
    
    # Annual maintenance costs for energy system (portion of maintenance OPEX)
    energy_maintenance_costs = maintenance_opex * 0.6  # Assuming 60% of maintenance is for energy system
    
    # Calculate LCOE
    lcoe = calculate_lcoe(
        capital_costs=energy_capital_costs,
        annual_maintenance=energy_maintenance_costs,
        system_lifetime=loan_years,
        annual_energy_production=total_annual_energy,
        discount_rate=interest_rate / 100,  # Convert percentage to decimal
        degradation_rate=energy_degradation_rate
    )
    
    # Calculate energy metrics
    lifetime_energy_production = 0
    for year in range(1, loan_years + 1):
        year_production = total_annual_energy * ((1 - energy_degradation_rate) ** (year - 1))
        lifetime_energy_production += year_production
    
    # Add energy and LCOE metrics to the results
    energy_metrics = {
        "solar_capacity_kw": solar_capacity_kw,
        "wind_capacity_kw": wind_capacity_kw,
        "solar_annual_energy": solar_annual_energy,
        "wind_annual_energy": wind_annual_energy,
        "total_annual_energy": total_annual_energy,
        "lifetime_energy_production": lifetime_energy_production,
        "lcoe": lcoe,
        "lcoe_cents": lcoe * 100  # Convert to Euro cents
    }

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
        },
        
        # Energy Metrics
        "energy_metrics": energy_metrics
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
        # Store the parameter value and corresponding CO2 savings
        results.append({
            'Parameter_Value': value,
            'CO2_Savings_Per_Outpost': result['co2_savings_per_outpost'],
            'CO2_Savings_All_Outposts': result['co2_savings_all_outposts'],
            'Manned_CO2_Emissions': result['manned_co2_emissions'] / 1000,  # Convert to tonnes
            'Autonomous_CO2_Emissions': result['autonomous_co2_emissions'] / 1000,  # Convert to tonnes
            'Cost_Efficiency': result['cost_efficiency_per_ton'],
            'Innovation_Fund_Score': result['innovation_fund_score']
        })
    
    return pd.DataFrame(results)