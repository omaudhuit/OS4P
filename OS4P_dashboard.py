#from fastapi import FastAPI
#from pydantic import BaseModel
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import uvicorn

# FastAPI instance
app = FastAPI()

# Streamlit UI (run separately)
st.set_page_config(page_title="OS4P Sensitivity Analysis Dashboard", layout="wide")

class CalculationInput(BaseModel):
    num_outposts: int
    fuel_consumption: float
    interest_rate: float
    loan_years: int
    sla_premium: float

# Function to calculate OS4P metrics
def calculate_os4p(num_outposts, fuel_consumption, interest_rate, loan_years, sla_premium):
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

    return {
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
        "monthly_debt_payment": monthly_debt_payment,
        "monthly_fee_unit": monthly_fee_unit
    }

@app.post("/")
async def calculate_results(input_data: CalculationInput):
    return calculate_os4p(**input_data.dict())

# Run API server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
