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
    
    return {
        "co2_savings_per_outpost": co2_savings_per_outpost,
        "co2_savings_all_outposts": co2_savings_all_outposts,
        "co2_savings_lifetime": co2_savings_lifetime,
        "monthly_debt_payment": monthly_debt_payment,
        "monthly_fee_unit": monthly_fee_unit
    }

def sensitivity_analysis_co2(base_params, sensitivity_params):
    """
    Perform sensitivity analysis on CO2 savings by varying key parameters
    and measuring their impact on CO2 savings metrics.
    """
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
                "co2_savings_lifetime": calculation["co2_savings_lifetime"],
                "monthly_debt_payment": calculation["monthly_debt_payment"],
                "monthly_fee_unit": calculation["monthly_fee_unit"]
            })
        
        results[param_name] = param_results
    
    return results

def generate_sensitivity_report(sensitivity_data, base_params):
    """
    Generate a report with tables and insights from the sensitivity analysis.
    """
    report = {}
    
    for param_name, param_results in sensitivity_data.items():
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(param_results)
        
        # Calculate percentage changes from base case
        base_case_index = None
        if param_name == "num_outposts":
            base_case_index = list(df["param_value"]).index(base_params["num_outposts"])
        elif param_name == "fuel_consumption":
            base_case_index = list(df["param_value"]).index(base_params["fuel_consumption"])
        elif param_name == "loan_years":
            base_case_index = list(df["param_value"]).index(base_params["loan_years"])
        elif param_name == "interest_rate":
            base_case_index = list(df["param_value"]).index(base_params["interest_rate"])
        elif param_name == "sla_premium":
            base_case_index = list(df["param_value"]).index(base_params["sla_premium"])
        
        base_case = df.iloc[base_case_index]
        
        df["pct_change_per_outpost"] = (df["co2_savings_per_outpost"] / base_case["co2_savings_per_outpost"] - 1) * 100
        df["pct_change_all_outposts"] = (df["co2_savings_all_outposts"] / base_case["co2_savings_all_outposts"] - 1) * 100
        df["pct_change_lifetime"] = (df["co2_savings_lifetime"] / base_case["co2_savings_lifetime"] - 1) * 100
        df["pct_change_monthly_fee"] = (df["monthly_fee_unit"] / base_case["monthly_fee_unit"] - 1) * 100
        
        # Calculate elasticity (% change in output / % change in input)
        for i, row in df.iterrows():
            if i != base_case_index and base_case["param_value"] != 0:
                pct_change_input = (row["param_value"] / base_case["param_value"] - 1) * 100
                if pct_change_input != 0:
                    df.at[i, "elasticity_lifetime"] = row["pct_change_lifetime"] / pct_change_input
                    df.at[i, "elasticity_monthly_fee"] = row["pct_change_monthly_fee"] / pct_change_input
        
        report[param_name] = df
    
    return report

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
    
    # Interest rate insights
    if "interest_rate" in report:
        interest_df = report["interest_rate"]
        min_rate = interest_df.iloc[0]["param_value"]
        max_rate = interest_df.iloc[-1]["param_value"]
        min_fee = interest_df.iloc[0]["monthly_fee_unit"]
        max_fee = interest_df.iloc[-1]["monthly_fee_unit"]
        
        insights.append(
            f"Interest rate has a significant impact on monthly fees. Increasing the rate from "
            f"{min_rate}% to {max_rate}% raises the monthly fee per outpost from "
            f"${min_fee:.2f} to ${max_fee:.2f}."
        )
    
    # SLA premium insights
    if "sla_premium" in report:
        sla_df = report["sla_premium"]
        sla_elasticity = sla_df["elasticity_monthly_fee"].dropna().mean()
        
        insights.append(
            f"SLA premium has a direct impact on monthly fees with an elasticity of approximately {sla_elasticity:.2f}. "
            f"This means a 10% increase in SLA premium results in approximately a {abs(sla_elasticity * 10):.1f}% increase in monthly fees."
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
    elif most_sensitive_param == "interest_rate":
        param_label = "interest rate"
    elif most_sensitive_param == "sla_premium":
        param_label = "SLA premium"
    
    insights.append(
        f"The sensitivity analysis indicates that CO₂ savings are most sensitive to changes in {param_label}. "
        f"This suggests that optimization efforts should prioritize this parameter for maximum environmental impact."
    )
    
    return insights

def plot_sensitivity_charts(sensitivity_data, parameter_type):
    """
    Create visualizations of the sensitivity analysis results.
    Return the figure for Streamlit to display.
    """
    fig, axes = plt.subplots(len(sensitivity_data), 1, figsize=(10, 5 * len(sensitivity_data)))
    
    # Handle the case where there's only one parameter
    if len(sensitivity_data) == 1:
        axes = [axes]
    
    for i, (param_name, param_results) in enumerate(sensitivity_data.items()):
        df = pd.DataFrame(param_results)
        
        # Create labels based on parameter name
        if param_name == "num_outposts":
            param_label = "Number of Outposts"
        elif param_name == "fuel_consumption":
            param_label = "Fuel Consumption (L/hr)"
        elif param_name == "loan_years":
            param_label = "Project Lifetime (years)"
        elif param_name == "interest_rate":
            param_label = "Interest Rate (%)"
        elif param_name == "sla_premium":
            param_label = "SLA Premium (%)"
        
        # Plot different metrics based on selected parameter type
        if parameter_type == "CO₂ Savings":
            if param_name == "fuel_consumption":
                axes[i].plot(df["param_value"], df["co2_savings_per_outpost"], 'o-', color='green')
                y_label = "CO₂ Savings per Outpost (tonnes/year)"
                title = f"Sensitivity of CO₂ Savings to {param_label}"
            else:
                axes[i].plot(df["param_value"], df["co2_savings_lifetime"], 'o-', color='green')
                y_label = "Lifetime CO₂ Savings (tonnes)"
                title = f"Sensitivity of CO₂ Savings to {param_label}"
        else:  # Financial Metrics
            axes[i].plot(df["param_value"], df["monthly_fee_unit"], 'o-', color='blue')
            y_label = "Monthly Fee per Outpost ($)"
            title = f"Sensitivity of Monthly Fee to {param_label}"
        
        axes[i].set_xlabel(param_label)
        axes[i].set_ylabel(y_label)
        axes[i].set_title(title)
        axes[i].grid(True, linestyle='--', alpha=0.7)
        
        # Add data points with labels
        for x, y in zip(df["param_value"], df["co2_savings_lifetime"] if parameter_type == "CO₂ Savings" and param_name != "fuel_consumption" 
                        else df["co2_savings_per_outpost"] if parameter_type == "CO₂ Savings" 
                        else df["monthly_fee_unit"]):
            axes[i].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0,10), ha='center')
    
    plt.tight_layout()
    return fig

def main():
    st.title("OS4P Sensitivity Analysis Dashboard")
    
    st.markdown("""
    This dashboard analyzes the sensitivity of CO₂ savings and financial metrics to various parameters 
    in the Outpost Security for Pipelines (OS4P) system. Adjust the parameters below to see how they 
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
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("CO₂ Savings per Outpost (tonnes/year)", f"{base_results['co2_savings_per_outpost']:.1f}")
        st.metric("Total CO₂ Savings per Year (tonnes)", f"{base_results['co2_savings_all_outposts']:.1f}")
    
    with col2:
        st.metric("Lifetime CO₂ Savings (tonnes)", f"{base_results['co2_savings_lifetime']:.1f}")
        st.metric("Monthly Debt Payment ($)", f"${base_results['monthly_debt_payment']:.2f}")
    
    with col3:
        st.metric("Monthly Fee per Outpost ($)", f"${base_results['monthly_fee_unit']:.2f}")
    
    # Sensitivity Analysis Section
    st.header("Sensitivity Analysis")
    
    # Allow user to choose parameters to analyze
    st.subheader("Select Parameters to Analyze")
    
    param_options = {
        "num_outposts": "Number of Outposts",
        "fuel_consumption": "Fuel Consumption (L/hr)",
        "interest_rate": "Interest Rate (%)",
        "loan_years": "Project Lifetime (years)",
        "sla_premium": "SLA Premium (%)"
    }
    
    selected_params = []
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.checkbox("Number of Outposts", value=True):
            selected_params.append("num_outposts")
        if st.checkbox("Fuel Consumption", value=True):
            selected_params.append("fuel_consumption")
    
    with col2:
        if st.checkbox("Interest Rate", value=False):
            selected_params.append("interest_rate")
        if st.checkbox("Project Lifetime", value=True):
            selected_params.append("loan_years")
    
    with col3:
        if st.checkbox("SLA Premium", value=False):
            selected_params.append("sla_premium")
    
    # Define ranges for sensitivity analysis
    sensitivity_params = {}
    
    if "num_outposts" in selected_params:
        sensitivity_params["num_outposts"] = np.arange(45, 200, 5)  # 1, 3, 5, ..., 19
    
    if "fuel_consumption" in selected_params:
        sensitivity_params["fuel_consumption"] = np.arange(5, 105, 10)  # 5, 15, 25, ..., 95
    
    if "interest_rate" in selected_params:
        sensitivity_params["interest_rate"] = np.arange(1.0, 16.0, 1.5)  # 1.0, 2.5, 4.0, ..., 14.5
    
    if "loan_years" in selected_params:
        sensitivity_params["loan_years"] = np.arange(5, 26, 5)  # 5, 10, 15, 20, 25
    
    if "sla_premium" in selected_params:
        sensitivity_params["sla_premium"] = np.arange(0.0, 55.0, 5.0)  # 0, 5, 10, ..., 50
    
    # Run sensitivity analysis if parameters are selected
    if selected_params:
        sensitivity_data = sensitivity_analysis_co2(base_params, sensitivity_params)
        report = generate_sensitivity_report(sensitivity_data, base_params)
        insights = generate_insights(report)
        
        # Select metric type for visualization
        metric_type = st.radio("Select Metric Type for Visualization", ["CO₂ Savings", "Financial Metrics"])
        
        # Create visualization
        fig = plot_sensitivity_charts(sensitivity_data, metric_type)
        st.pyplot(fig)
        
        # Display insights
        st.subheader("Key Insights")
        for insight in insights:
            st.write(f"• {insight}")
        
        # Display detailed data tables
        st.subheader("Detailed Data Tables")
        
        for param_name, df in report.items():
            if param_name in selected_params:
                st.subheader(param_options[param_name])
                
                # Format the DataFrame for display
                display_df = df[["param_value", "co2_savings_per_outpost", "co2_savings_lifetime", "monthly_fee_unit"]].copy()
                display_df.columns = ["Parameter Value", "CO₂ Savings per Outpost (tonnes/year)", 
                                    "Lifetime CO₂ Savings (tonnes)", "Monthly Fee per Outpost ($)"]
                
                # Round numeric columns
                for col in display_df.columns[1:]:
                    display_df[col] = display_df[col].round(2)
                
                st.dataframe(display_df)
    else:
        st.warning("Please select at least one parameter to analyze.")

if __name__ == "__main__":
    main() 