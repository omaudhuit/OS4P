import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="OS4P Sensitivity Analysis Dashboard", layout="wide")

def calculate_os4p(num_outposts, fuel_consumption, interest_rate, loan_years, sla_premium):
    # Constants
    operating_days_per_year = 300
    co2_factor = 1.0  # kg CO₂ per liter
    maintenance_emissions = 1594.3
    microgrid_capex = 110000
    drones_capex = 60000
    
    # CO₂ Savings Calculation
    daily_fuel_consumption = fuel_consumption * 8 + 2.5 * 24
    annual_fuel_consumption = daily_fuel_consumption * operating_days_per_year
    manned_co2_emissions = annual_fuel_consumption * co2_factor
    autonomous_co2_emissions = maintenance_emissions
    co2_savings_per_outpost = (manned_co2_emissions - autonomous_co2_emissions) / 1000
    co2_savings_all_outposts = co2_savings_per_outpost * num_outposts
    co2_savings_lifetime = co2_savings_all_outposts * loan_years
    
    # Financial Calculations
    total_capex = (microgrid_capex + drones_capex) * num_outposts
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
        "cost_efficiency_lifetime": cost_efficiency_lifetime
    }

def main():
    st.title("OS4P Sensitivity Analysis Dashboard")
    
    st.markdown("""
    This dashboard analyzes the sensitivity of CO₂ savings and financial metrics to various parameters 
    of the OS4P system. Adjust the parameters below to see how they 
    impact environmental and financial outcomes.
    """)
    
    st.header("Base Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_outposts = st.slider("Number of Outposts", 45, 200, 5)
        fuel_consumption = st.slider("Fuel Consumption (L/hr)", 5, 100, 25)
    
    with col2:
        interest_rate = st.slider("Interest Rate (%)", 1.0, 15.0, 5.0, 0.5)
        loan_years = st.slider("Project Lifetime (years)", 3, 25, 10)
    
    with col3:
        sla_premium = st.slider("SLA Premium (%)", 0.0, 50.0, 15.0, 5.0)
    
    # Base parameters dictionary
    base_params = {
        "num_outposts": num_outposts,
        "fuel_consumption": fuel_consumption,
        "interest_rate": interest_rate,
        "loan_years": loan_years,
        "sla_premium": sla_premium
    }
    
    # Calculate base case results
    base_results = calculate_os4p(**base_params)
    
    # Display base case metrics
    st.header("Base Case Results")

    # Debugging Output
    st.write("DEBUG: Base Results Keys:", base_results.keys())
    st.write("DEBUG: Full Base Results:", base_results)

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
        st.metric("Cost Efficiency (Lifetime) (€/tCO₂)", f"€{base_results['cost_efficiency_lifetime']:.0f}")

if __name__ == "__main__":
    main()
