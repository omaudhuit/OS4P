import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, jsonify

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
    
    return {
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
        "monthly_debt_payment": monthly_debt_payment,
        "monthly_fee_unit": monthly_fee_unit
    }

def sensitivity_analysis_co2():
    """
    Perform sensitivity analysis on CO2 savings by varying key parameters
    and measuring their impact on CO2 savings metrics.
    """
    # Base case parameters
    base_params = {
        "num_outposts": 5,
        "fuel_consumption": 25,  # liters per hour
        "interest_rate": 5.0,    # percentage
        "loan_years": 10,
        "sla_premium": 15.0      # percentage
    }
    
    # Parameters to vary and their ranges
    sensitivity_params = {
        "num_outposts": np.arange(1, 11),
        "fuel_consumption": np.arange(5, 55, 5),
        "loan_years": np.arange(5, 21, 5)
    }
    
    results = {}
    
    # Analyze each parameter's impact
    for param_name, param_values in sensitivity_params.items():
        param_results = []
        
        for value in param_values:
            # Create a copy of base parameters and modify the one we're testing
            test_params = base_params.copy()
            test_params[param_name] = value
            
            # Calculate metrics with the modified parameter
            calculation = calculate_os4p(**test_params)
            
            # Store results for this parameter value
            param_results.append({
                "param_value": value,
                "co2_savings_per_outpost": calculation["co2_savings_per_outpost"],
                "co2_savings_all_outposts": calculation["co2_savings_all_outposts"],
                "co2_savings_lifetime": calculation["co2_savings_lifetime"]
            })
        
        results[param_name] = param_results
    
    return results

def generate_sensitivity_report():
    """
    Generate a report with tables and insights from the sensitivity analysis.
    """
    sensitivity_data = sensitivity_analysis_co2()
    report = {}
    
    for param_name, param_results in sensitivity_data.items():
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(param_results)
        
        # Calculate percentage changes from base case
        base_case_index = None
        if param_name == "num_outposts":
            base_case_index = list(df["param_value"]).index(5)
        elif param_name == "fuel_consumption":
            base_case_index = list(df["param_value"]).index(25)
        elif param_name == "loan_years":
            base_case_index = list(df["param_value"]).index(10)
        
        base_case = df.iloc[base_case_index]
        
        df["pct_change_per_outpost"] = (df["co2_savings_per_outpost"] / base_case["co2_savings_per_outpost"] - 1) * 100
        df["pct_change_all_outposts"] = (df["co2_savings_all_outposts"] / base_case["co2_savings_all_outposts"] - 1) * 100
        df["pct_change_lifetime"] = (df["co2_savings_lifetime"] / base_case["co2_savings_lifetime"] - 1) * 100
        
        # Calculate elasticity (% change in output / % change in input)
        for i, row in df.iterrows():
            if i != base_case_index and base_case["param_value"] != 0:
                pct_change_input = (row["param_value"] / base_case["param_value"] - 1) * 100
                if pct_change_input != 0:
                    df.at[i, "elasticity_lifetime"] = row["pct_change_lifetime"] / pct_change_input
        
        report[param_name] = df
    
    return report

def plot_sensitivity_charts():
    """
    Create visualizations of the sensitivity analysis results.
    """
    sensitivity_data = sensitivity_analysis_co2()
    
    # Set up the figure with subplots
    fig, axes = plt.subplots(len(sensitivity_data), 1, figsize=(10, 15))
    
    for i, (param_name, param_results) in enumerate(sensitivity_data.items()):
        df = pd.DataFrame(param_results)
        
        # Create labels based on parameter name
        if param_name == "num_outposts":
            param_label = "Number of Outposts"
            y_label = "Lifetime CO₂ Savings (tonnes)"
        elif param_name == "fuel_consumption":
            param_label = "Fuel Consumption (L/hr)"
            y_label = "CO₂ Savings per Outpost (tonnes/year)"
        elif param_name == "loan_years":
            param_label = "Project Lifetime (years)"
            y_label = "Lifetime CO₂ Savings (tonnes)"
        
        # Plot different metrics based on parameter
        if param_name == "num_outposts":
            axes[i].plot(df["param_value"], df["co2_savings_lifetime"], 'o-', color='green')
            axes[i].set_ylabel(y_label)
        elif param_name == "fuel_consumption":
            axes[i].plot(df["param_value"], df["co2_savings_per_outpost"], 'o-', color='blue')
            axes[i].set_ylabel(y_label)
        elif param_name == "loan_years":
            axes[i].plot(df["param_value"], df["co2_savings_lifetime"], 'o-', color='purple')
            axes[i].set_ylabel(y_label)
        
        axes[i].set_xlabel(param_label)
        axes[i].set_title(f"Sensitivity of CO₂ Savings to {param_label}")
        axes[i].grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    return fig

def generate_insights(report):
    """
    Generate insights from the sensitivity analysis.
    """
    insights = []
    
    # Fuel consumption insights
    if "fuel_consumption" in report:
        fuel_df = report["fuel_consumption"]
        min_fuel = fuel_df.iloc[0]["param_value"]
        max_fuel = fuel_df.iloc[-1]["param_value"]
        min_savings = fuel_df.iloc[0]["co2_savings_per_outpost"]
        max_savings = fuel_df.iloc[-1]["co2_savings_per_outpost"]
        
        fuel_elasticity = fuel_df["elasticity_lifetime"].dropna().mean()
        
        insights.append(
            f"Fuel consumption has a direct linear impact on CO₂ savings. Increasing fuel consumption "
            f"from {min_fuel} L/hr to {max_fuel} L/hr increases annual CO₂ savings per outpost "
            f"from {min_savings:.1f} tonnes to {max_savings:.1f} tonnes."
        )
        
        if abs(fuel_elasticity) > 0:
            insights.append(
                f"The elasticity of CO₂ savings with respect to fuel consumption is approximately {fuel_elasticity:.2f}, "
                f"meaning a 1% increase in fuel consumption results in a {abs(fuel_elasticity):.2f}% increase in lifetime CO₂ savings."
            )
    
    # Number of outposts insights
    if "num_outposts" in report:
        outpost_df = report["num_outposts"]
        outpost_elasticity = outpost_df["elasticity_lifetime"].dropna().mean()
        
        if abs(outpost_elasticity) > 0:
            insights.append(
                f"The relationship between number of outposts and total CO₂ savings is proportional with an "
                f"elasticity of {outpost_elasticity:.2f}. This means doubling the number of outposts "
                f"approximately doubles the total lifetime CO₂ savings."
            )
    
    # Project lifetime insights
    if "loan_years" in report:
        years_df = report["loan_years"]
        min_years = years_df.iloc[0]["param_value"]
        max_years = years_df.iloc[-1]["param_value"]
        min_lifetime = years_df.iloc[0]["co2_savings_lifetime"]
        max_lifetime = years_df.iloc[-1]["co2_savings_lifetime"]
        
        insights.append(
            f"Extending the project lifetime from {min_years} to {max_years} years increases total CO₂ savings "
            f"from {min_lifetime:.1f} tonnes to {max_lifetime:.1f} tonnes, showing the cumulative "
            f"environmental benefit of longer-term deployments."
        )
    
    # Overall recommendation
    most_sensitive_param = ""
    highest_elasticity = 0
    
    for param_name, df in report.items():
        avg_elasticity = abs(df["elasticity_lifetime"].dropna().mean())
        if avg_elasticity > highest_elasticity:
            highest_elasticity = avg_elasticity
            most_sensitive_param = param_name
    
    if most_sensitive_param == "fuel_consumption":
        param_label = "fuel consumption"
    elif most_sensitive_param == "num_outposts":
        param_label = "number of outposts"
    elif most_sensitive_param == "loan_years":
        param_label = "project lifetime"
    
    insights.append(
        f"The sensitivity analysis indicates that CO₂ savings are most sensitive to changes in {param_label}. "
        f"This suggests that optimization efforts should prioritize this parameter for maximum environmental impact."
    )
    
    return insights

# Add this function to the app.py to integrate with your Flask application
def integrate_sensitivity_analysis():
    @app.route("/sensitivity-analysis")
    def sensitivity_analysis_page():
        report = generate_sensitivity_report()
        insights = generate_insights(report)
        
        # Convert DataFrames to HTML tables
        tables = {}
        for param_name, df in report.items():
            tables[param_name] = df.to_html(classes='table table-striped', index=False)
        
        return render_template("sensitivity.html", tables=tables, insights=insights)