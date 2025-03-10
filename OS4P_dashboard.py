import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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

    # CAPEX Inputs (User-defined)
    capex_microgrid = params["capex_microgrid"]
    capex_drones = params["capex_drones"]
    capex_bos = params["capex_bos"]

    # OPEX Inputs (User-defined)
    opex_maintenance = params["opex_maintenance"]
    opex_communications = params["opex_communications"]
    opex_security = params["opex_security"]

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

    # Financial Calculations (User-defined CAPEX Breakdown)
    total_capex = (capex_microgrid + capex_drones + capex_bos) * num_outposts
    total_opex = (opex_maintenance + opex_communications + opex_security) * num_outposts

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
        "total_opex": total_opex,
        "capex_breakdown": {
            "Microgrid CAPEX": capex_microgrid * num_outposts,
            "Drones CAPEX": capex_drones * num_outposts,
            "Balance of System CAPEX": capex_bos * num_outposts,
        },
        "opex_breakdown": {
            "Maintenance OPEX": opex_maintenance * num_outposts,
            "Communications OPEX": opex_communications * num_outposts,
            "Security OPEX": opex_security * num_outposts,
        }
    }

def main():
    st.title("OS4P Interactive Dashboard")
    
    st.markdown("### Configure Your OS4P System Below")
    
    # User Input Fields
    with st.sidebar:
        st.header("User Inputs")

        num_outposts = st.number_input("Number of Outposts", min_value=1, max_value=200, value=10, step=1, format="%d")
        
        st.header("Fuel Consumption Inputs (Liters per Hour)")
        large_patrol_fuel = st.number_input("Large Patrol Boat Fuel", min_value=50, max_value=300, value=150, step=10, format="%d")
        rib_fuel = st.number_input("RIB Boat Fuel", min_value=10, max_value=100, value=50, step=5, format="%d")
        small_patrol_fuel = st.number_input("Small Patrol Boat Fuel", min_value=5, max_value=50, value=30, step=5, format="%d")
        hours_per_day_base = st.number_input("Patrol Hours per Day", min_value=4, max_value=24, value=8, step=1, format="%d")

        st.header("CAPEX Inputs (€ per Outpost)")
        capex_microgrid = st.number_input("Microgrid CAPEX", min_value=50000, max_value=200000, value=110000, step=5000, format="%d")
        capex_drones = st.number_input("Drones CAPEX", min_value=20000, max_value=100000, value=60000, step=5000, format="%d")
        capex_bos = st.number_input("Balance of System CAPEX", min_value=10000, max_value=50000, value=30000, step=5000, format="%d")

        st.header("OPEX Inputs (€ per Outpost)")
        opex_maintenance = st.number_input("Maintenance OPEX", min_value=5000, max_value=50000, value=10000, step=5000, format="%d")
        opex_communications = st.number_input("Communications OPEX", min_value=5000, max_value=50000, value=15000, step=5000, format="%d")
        opex_security = st.number_input("Security OPEX", min_value=5000, max_value=50000, value=20000, step=5000, format="%d")

    # Store user inputs in dictionary
    params = {key: value for key, value in locals().items() if key in calculate_os4p.__code__.co_varnames}
    
    # Calculate results
    base_results = calculate_os4p(params)

    # Display results
    st.header("Base Case Results")

    st.metric("CO₂ Savings per Outpost (tonnes/year)", f"{base_results['co2_savings_per_outpost']:.1f}")
    st.metric("Total CAPEX (€)", f"€{base_results['total_capex']:,.0f}")
    st.metric("Total OPEX (€)", f"€{base_results['total_opex']:,.0f}")

    # CAPEX Breakdown
    st.header("CAPEX Breakdown")
    st.dataframe(pd.DataFrame.from_dict(base_results["capex_breakdown"], orient='index', columns=["Amount (€)"]))

    # OPEX Breakdown
    st.header("OPEX Breakdown")
    st.dataframe(pd.DataFrame.from_dict(base_results["opex_breakdown"], orient='index', columns=["Amount (€)"]))

if __name__ == "__main__":
    main()
