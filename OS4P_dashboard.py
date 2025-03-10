import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="OS4P Interactive Dashboard", layout="wide")

def calculate_os4p(params):
    # Extracting user-defined constants
    num_outposts = params["num_outposts"]
    fuel_consumption = params["fuel_consumption"]
    interest_rate = params["interest_rate"]
    loan_years = params["loan_years"]
    sla_premium = params["sla_premium"]
    
    operating_days_per_year = params["operating_days_per_year"]
    co2_factor = params["co2_factor"]
    maintenance_emissions = params["maintenance_emissions"]

    # CAPEX Inputs
    microgrid_capex = params["microgrid_capex"]
    drones_capex = params["drones_capex"]
    communication_capex = params["communication_capex"]
    security_capex = params["security_capex"]
    installation_capex = params["installation_capex"]

    # CO₂ Savings Calculation
    daily_fuel_consumption = fuel_consumption * 8 + 2.5 * 24
    annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year
    manned_co2_emissions = annual_fuel_consumption * co2_factor
    autonomous_co2_emissions = maintenance_emissions
    co2_savings_per_outpost = (manned_co2_emissions - autonomous_co2_emissions) / 1000
    co2_savings_all_outposts = co2_savings_per_outpost * num_outposts
    co2_savings_lifetime = co2_savings_all_outposts * loan_years

    # Financial Calculations (User-defined CAPEX Breakdown)
    total_capex = (microgrid_capex + drones_capex + communication_capex + security_capex + installation_capex) * num_outposts
    pilot_markup = total_capex * 1.25
    grant_coverage = 0.60
    total_grant = grant_coverage * pilot_markup
    debt = pilot_markup - total_grant

    # Loan Calculation
    monthly_interest_rate = interest_rate / 100 / 12
    num_months = loan_years * 12
    monthly_debt_payment = (debt * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -num_months)

    # SLA Premium
    sla_multiplier = 1 + sla_premium / 100
    monthly_fee_unit = (monthly_debt_payment / num_outposts) * sla_multiplier

    # ✅ Cost Efficiency Calculation
    cost_efficiency_per_ton = total_grant / co2_savings_all_outposts if co2_savings_all_outposts > 0 else float('inf')
    cost_efficiency_lifetime = total_grant / co2_savings_lifetime if co2_savings_lifetime > 0 else float('inf')

    return {
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
        "monthly_debt_payment": monthly_debt_payment,
        "monthly_fee_unit": monthly_fee_unit,
        "cost_efficiency_per_ton": cost_efficiency_per_ton,
        "cost_efficiency_lifetime": cost_efficiency_lifetime,
        "total_capex": total_capex,
        "capex_breakdown": {
            "Microgrid CAPEX": microgrid_capex * num_outposts,
            "Drones CAPEX": drones_capex * num_outposts,
            "Communication CAPEX": communication_capex * num_outposts,
            "Security CAPEX": security_capex * num_outposts,
            "Installation CAPEX": installation_capex * num_outposts,
        }
    }

def main():
    st.title("OS4P Interactive Dashboard")
    
    st.markdown("### Configure Your OS4P System Below")
    
    # User Input Fields
    with st.sidebar:
        st.header("User Inputs")

        num_outposts = st.number_input("Number of Outposts", min_value=1, max_value=200, value=10, step=1, format="%d")
        fuel_consumption = st.number_input("Manned Fuel Consumption (L/hr)", min_value=1, max_value=100, value=25, step=1, format="%d")
        interest_rate = st.number_input("Interest Rate (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.1, format="%.1f")
        loan_years = st.number_input("Project Lifetime (years)", min_value=3, max_value=25, value=10, step=1, format="%d")
        sla_premium = st.number_input("SLA Premium (%)", min_value=0.0, max_value=50.0, value=15.0, step=1.0, format="%.1f")

        st.header("Operational Parameters")
        operating_days_per_year = st.number_input("Operating Days per Year", min_value=200, max_value=365, value=300, step=1, format="%d")
        co2_factor = st.number_input("CO₂ Factor (kg CO₂ per liter)", min_value=0.5, max_value=3.0, value=1.0, step=0.1, format="%.1f")
        maintenance_emissions = st.number_input("Maintenance Emissions (kg CO₂)", min_value=500, max_value=5000, value=1594, step=10, format="%d")

        st.header("CAPEX Inputs (€ per Outpost)")
        microgrid_capex = st.number_input("Microgrid CAPEX", min_value=50000, max_value=200000, value=110000, step=5000, format="%d")
        drones_capex = st.number_input("Drones CAPEX", min_value=20000, max_value=100000, value=60000, step=5000, format="%d")
        communication_capex = st.number_input("Communication CAPEX", min_value=10000, max_value=50000, value=30000, step=5000, format="%d")
        security_capex = st.number_input("Security CAPEX", min_value=10000, max_value=50000, value=25000, step=5000, format="%d")
        installation_capex = st.number_input("Installation CAPEX", min_value=5000, max_value=30000, value=15000, step=5000, format="%d")

    # Store user inputs in dictionary
    params = locals()
    
    # Calculate results
    base_results = calculate_os4p(params)

    # Display results
    st.header("Base Case Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("CO₂ Savings per Outpost (tonnes/year)", f"{base_results['co2_savings_per_outpost']:.1f}")
        st.metric("Total CO₂ Savings per Year (tonnes)", f"{base_results['co2_savings_all_outposts']:.1f}")

    with col2:
        st.metric("Lifetime CO₂ Savings (tonnes)", f"{base_results['co2_savings_lifetime']:.1f}")
        st.metric("Monthly Debt Payment (€)", f"€{base_results['monthly_debt_payment']:.2f}")

    with col3:
        st.metric("Monthly Fee per Outpost (€)", f"€{base_results['monthly_fee_unit']:.2f}")
        st.metric("Cost Efficiency per Ton (€/tCO₂)", f"€{base_results['cost_efficiency_per_ton']:.0f}")

    # CAPEX Breakdown
    st.header("Full CAPEX Breakdown")
    capex_df = pd.DataFrame.from_dict(base_results["capex_breakdown"], orient='index', columns=["Amount (€)"])
    st.dataframe(capex_df)

if __name__ == "__main__":
    main()
