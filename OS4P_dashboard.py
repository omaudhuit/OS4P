import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="OS4P Interactive Dashboard", layout="wide")

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
    
    # Total Cost of Ownership (TCO)
    tco = total_capex + lifetime_opex
    tco_per_outpost = tco / num_outposts

    return {
        # CO2 Metrics
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
        
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
        
        # Project Financing 
        "pilot_markup": pilot_markup,
        "total_grant": total_grant,
        "debt": debt,
        "lifetime_debt_payment": lifetime_debt_payment,
        
        # Breakdowns for visualizations
        "capex_breakdown": {
            "Microgrid": microgrid_capex * num_outposts,
            "Drones": drones_capex * num_outposts,
            "BOS (Balance of System)": bos_capex * num_outposts
        },
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

def create_cost_breakdown_chart(capex_data, opex_data):
    capex_df = pd.DataFrame(list(capex_data.items()), columns=['Category', 'Value'])
    capex_df['Type'] = 'CAPEX'
    
    opex_df = pd.DataFrame(list(opex_data.items()), columns=['Category', 'Value'])
    opex_df['Type'] = 'OPEX (Annual)'
    
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

        st.subheader("CAPEX Inputs (€ per Outpost)")
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
        "microgrid_capex": microgrid_capex,
        "drones_capex": drones_capex,
        "bos_capex": bos_capex,
        "maintenance_opex": maintenance_opex,
        "communications_opex": communications_opex,
        "security_opex": security_opex
    }
    
    # Calculate results
    results = calculate_os4p(params)

    # Display comprehensive results in the main area
    st.header("Base Case Results")
    
    # Create tabs for organized display
    tab1, tab2, tab3 = st.tabs(["Overview", "Financial Details", "Visualizations"])
    
    with tab1:
        # CO2 metrics
        st.subheader("Environmental Impact")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("CO₂ Savings per Outpost (tonnes/year)", f"{results['co2_savings_per_outpost']:.1f}")
        with col2:
            st.metric("Total CO₂ Savings per Year (tonnes)", f"{results['co2_savings_all_outposts']:.1f}")
        with col3:
            st.metric("Lifetime CO₂ Savings (tonnes)", f"{results['co2_savings_lifetime']:.1f}")
        
        # Cost metrics
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
        
        # Efficiency metrics
        st.subheader("Efficiency Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Cost per Tonne CO₂ Saved (€/tonne/year)", f"{results['cost_efficiency_per_ton']:,.0f}")
        with col2:
            st.metric("Lifetime Cost per Tonne CO₂ Saved (€/tonne)", f"{results['cost_efficiency_lifetime']:,.0f}")
    
    with tab2:
        # Financial details
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
        
        # CAPEX Breakdown
        st.subheader("CAPEX Breakdown")
        capex_df = pd.DataFrame.from_dict(results["capex_breakdown"], orient='index', columns=["Amount (€)"])
        capex_df["Percentage"] = (capex_df["Amount (€)"] / capex_df["Amount (€)"].sum() * 100).round(1).astype(str) + '%'
        st.dataframe(capex_df)
        
        # OPEX Breakdown
        st.subheader("Annual OPEX Breakdown")
        opex_df = pd.DataFrame.from_dict(results["opex_breakdown"], orient='index', columns=["Amount (€)"])
        opex_df["Percentage"] = (opex_df["Amount (€)"] / opex_df["Amount (€)"].sum() * 100).round(1).astype(str) + '%'
        st.dataframe(opex_df)
    
    with tab3:
        # Cost breakdown visualization
        st.subheader("Cost Breakdown Visualization")
        cost_chart = create_cost_breakdown_chart(results["capex_breakdown"], results["opex_breakdown"])
        st.plotly_chart(cost_chart)
        
        # CO2 comparison visualization
        st.subheader("CO₂ Emissions Comparison")
        co2_chart = create_co2_comparison_chart(results["co2_factors"])
        st.plotly_chart(co2_chart)

if __name__ == "__main__":
    main()