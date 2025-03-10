with tab5:
        st.header("Levelized Cost of Energy (LCOE) Analysis")
        
        # Explanation of LCOE
        with st.expander("What is LCOE?"):
            st.markdown("""
            **Levelized Cost of Energy (LCOE)** represents the average cost per unit of electricity generated over the lifetime of an energy system. It is calculated by:
            
            1. Summing all lifetime costs (CAPEX and OPEX) in present value terms
            2. Dividing by the total energy production in present value terms
            
            LCOE allows for comparison between different energy generation technologies regardless of their scale, lifetime, or capital cost structure.
            
            **Formula:**
            
            ```
            LCOE = (Present Value of Total Lifetime Costs) / (Present Value of Total Lifetime Energy Production)
            ```
            
            Lower LCOE values indicate more cost-effective energy generation.
            """)
        
        # Display LCOE metrics
        st.subheader("LCOE Results for Microgrid")
        
        # Main LCOE display
        lcoe_value = results['lcoe']
        
        col1, col2 = st.columns(2)
        with col1:
            # Format LCOE for display
            if lcoe_value < 1:
                lcoe_display = f"{lcoe_value:.3f} €/kWh"
            else:
                lcoe_display = f"{lcoe_value:.2f} €/kWh"
                
            st.metric("Levelized Cost of Energy", lcoe_display)
            
            # Compare to benchmarks
            if lcoe_value <= 0.10:
                st.success("Excellent - Competitive with utility-scale renewables")
            elif lcoe_value <= 0.20:
                st.info("Good - Competitive with residential solar")
            elif lcoe_value <= 0.30:
                st.warning("Moderate - Cheaper than diesel generation but higher than grid power")
            else:
                st.error("High - Consider optimizing the energy system design")
        
        with col2:
            st.metric("Annual Energy Production", f"{results['annual_energy_production']:.0f} kWh")
            st.metric("Energy System CAPEX", f"€{results['energy_capex']:,.0f}")
            st.metric("Energy System OPEX (Annual)", f"€{results['energy_opex']:,.0f}")
        
        # Energy production breakdown
        st.subheader("Energy Production Breakdown")
        
        col1, col2 = st.columns(2)
        with col1:
            energy_pie = create_energy_production_chart(results["energy_breakdown"])
            st.plotly_chart(energy_pie, use_container_width=True)
        
        with col2:
            # Display energy production details
            solar_percentage = (results['solar_annual_production'] / results['annual_energy_production']) * 100 if results['annual_energy_production'] > 0 else 0
            wind_percentage = (results['wind_annual_production'] / results['annual_energy_production']) * 100 if results['annual_energy_production'] > 0 else 0
            
            st.metric("Solar Production", f"{results['solar_annual_production']:.0f} kWh/year ({solar_percentage:.1f}%)")
            st.metric("Wind Production", f"{results['wind_annual_production']:.0f} kWh/year ({wind_percentage:.1f}%)")
            
            # Calculate capacity factors
            solar_hours = results['solar_annual_production'] / params.get('solar_capacity_kw', 10)
            wind_hours = results['wind_annual_production'] / params.get('wind_capacity_kw', 3)
            
            st.metric("Solar Equivalent Full Load Hours", f"{solar_hours:.0f} hours/year")
            st.metric("Wind Equivalent Full Load Hours", f"{wind_hours:.0f} hours/year")
        
        # LCOE gauge chart
        st.subheader("LCOE Comparison")
        lcoe_gauge = create_lcoe_comparison_chart(lcoe_value)
        st.plotly_chart(lcoe_gauge, use_container_width=True)
        
        # LCOE Sensitivity Analysis
        st.subheader("LCOE Sensitivity Analysis")
        
        st.markdown("""
        Explore how different parameters affect the LCOE of your microgrid system.
        Select parameters to analyze and their ranges:
        """)
        
        # Parameter selection
        col1, col2 = st.columns(2)
        
        with col1:
            # First parameter selection
            lcoe_param1 = st.selectbox(
                "First Parameter:", 
                ["solar_capacity_kw", "wind_capacity_kw", "interest_rate", "loan_years"],
                format_func=lambda x: {
                    "solar_capacity_kw": "Solar Capacity (kW)",
                    "wind_capacity_kw": "Wind Capacity (kW)",
                    "interest_rate": "Interest Rate (%)",
                    "loan_years": "System Lifetime (years)"
                }.get(x, x)
            )
            
            # Define range based on selected parameter
            if lcoe_param1 == "solar_capacity_kw":
                p1_min, p1_max, p1_steps = 5, 20, 4
            elif lcoe_param1 == "wind_capacity_kw":
                p1_min, p1_max, p1_steps = 1, 6, 6
            elif lcoe_param1 == "interest_rate":
                p1_min, p1_max, p1_steps = 1, 10, 5
            elif lcoe_param1 == "loan_years":
                p1_min, p1_max, p1_steps = 5, 25, 5
            
            p1_min_val = st.number_input(f"Min {lcoe_param1}", value=float(p1_min), step=0.5)
            p1_max_val = st.number_input(f"Max {lcoe_param1}", value=float(p1_max), step=0.5)
        
        with col2:
            # Second parameter selection
            lcoe_param2 = st.selectbox(
                "Second Parameter:", 
                ["wind_capacity_kw", "solar_capacity_kw", "interest_rate", "loan_years"],
                index=1,
                format_func=lambda x: {
                    "solar_capacity_kw": "Solar Capacity (kW)",
                    "wind_capacity_kw": "Wind Capacity (kW)",
                    "interest_rate": "Interest Rate (%)",
                    "loan_years": "System Lifetime (years)"
                }.get(x, x)
            )
            
            # Define range based on selected parameter
            if lcoe_param2 == "solar_capacity_kw":
                p2_min, p2_max, p2_steps = 5, 20, 4
            elif lcoe_param2 == "wind_capacity_kw":
                p2_min, p2_max, p2_steps = 1, 6, 6
            elif lcoe_param2 == "interest_rate":
                p2_min, p2_max, p2_steps = 1, 10, 5
            elif lcoe_param2 == "loan_years":
                p2_min, p2_max, p2_steps = 5, 25, 5
            
            p2_min_val = st.number_input(f"Min {lcoe_param2}", value=float(p2_min), step=0.5)
            p2_max_val = st.number_input(f"Max {lcoe_param2}", value=float(p2_max), step=0.5)
        
        # Number of analysis points for each parameter
        num_steps = st.slider("Analysis resolution (points per parameter)", min_value=3, max_value=10, value=5)
        
        # Run LCOE sensitivity analysis button
        if st.button("Run LCOE Sensitivity Analysis"):
            # Prepare parameter variations
            variable_params = {
                lcoe_param1: [p1_min_val, p1_max_val, num_steps],
                lcoe_param2: [p2_min_val, p2_max_val, num_steps]
            }
            
            # Run analysis
            with st.spinner("Calculating LCOE sensitivity..."):
                lcoe_sensitivity_results = perform_lcoe_sensitivity_analysis(params, variable_params)
            
            # Create heatmap of results
            fig = px.density_heatmap(
                lcoe_sensitivity_results, 
                x=lcoe_param1, 
                y=lcoe_param2, 
                z="LCOE",
                labels={
                    lcoe_param1: {
                        "solar_capacity_kw": "Solar Capacity (kW)",
                        "wind_capacity_kw": "Wind Capacity (kW)",
                        "interest_rate": "Interest Rate (%)",
                        "loan_years": "System Lifetime (years)"
                    }.get(lcoe_param1, lcoe_param1),
                    lcoe_param2: {
                        "solar_capacity_kw": "Solar Capacity (kW)",
                        "wind_capacity_kw": "Wind Capacity (kW)",
                        "interest_rate": "Interest Rate (%)",
                        "loan_years": "System Lifetime (years)"
                    }.get(lcoe_param2, lcoe_param2),
                    "LCOE": "LCOE (€/kWh)"
                },
                title=f"LCOE Sensitivity to {lcoe_param1} and {lcoe_param2}",
                color_continuous_scale="RdYlGn_r"  # Reversed scale (red = high LCOE, green = low LCOE)
            )
            
            # Update layout for better readability
            fig.update_layout(
                height=500,
                coloraxis_colorbar=dict(
                    title="LCOE (€/kWh)"
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add interpretation
            st.markdown("### Interpretation Guide")
            st.markdown("""
            - **Green areas** represent parameter combinations with **lower LCOE** (more cost-effective)
            - **Red areas** represent parameter combinations with **higher LCOE** (less cost-effective)
            - Use this analysis to identify optimal parameter combinations for your microgrid system
            """)
            
            # Optimal point identification
            min_lcoe_row = lcoe_sensitivity_results.loc[lcoe_sensitivity_results['LCOE'].idxmin()]
            st.success(f"**Optimal configuration found:** {lcoe_param1} = {min_lcoe_row[lcoe_param1]:.2f}, {lcoe_param2} = {min_lcoe_row[lcoe_param2]:.2f}, yielding LCOE = {min_lcoe_row['LCOE']:.4f} €/kWh")
        
        # Single parameter LCOE sensitivity
        st.subheader("Single Parameter LCOE Sensitivity")
        
        lcoe_single_param = st.selectbox(
            "Parameter to analyze:", 
            ["solar_capacity_kw", "wind_capacity_kw", "interest_rate", "loan_years", "battery_capacity_kwh"],
            format_func=lambda x: {
                "solar_capacity_kw": "Solar Capacity (kW)",
                "wind_capacity_kw": "Wind Capacity (kW)",
                "interest_rate": "Interest Rate (%)",
                "loan_years": "System Lifetime (years)",
                "battery_capacity_kwh": "Battery Capacity (kWh)"
            }.get(x, x)
        )
        
        # Define range based on selected parameter
        if lcoe_single_param == "solar_capacity_kw":
            single_min, single_max, single_default, single_step = 5, 30, params.get("solar_capacity_kw", 10), 2.5
        elif lcoe_single_param == "wind_capacity_kw":
            single_min, single_max, single_default, single_step = 0, 10, params.get("wind_capacity_kw", 3), 1
        elif lcoe_single_param == "interest_rate":
            single_min, single_max, single_default, single_step = 1, 15, params.get("interest_rate", 5), 1
        elif lcoe_single_param == "loan_years":
            single_min, single_max, single_default, single_step = 5, 25, params.get("loan_years", 10), 2
        elif lcoe_single_param == "battery_capacity_kwh":
            single_min, single_max, single_default, single_step = 10, 100, params.get("battery_capacity_kwh", 30), 10
        
        single_range_min = st.number_input(f"Minimum {lcoe_single_param}", min_value=float(single_min), max_value=float(single_max), value=float(single_min), step=float(single_step))
        single_range_max = st.number_input(f"Maximum {lcoe_single_param}", min_value=float(single_min), max_value=float(single_max), value=float(single_max), step=float(single_step))
        single_num_steps = st.slider("Number of analysis points", min_value=5, max_value=20, value=10)
        
        if st.button("Run Single Parameter Analysis"):
            # Generate range values
            if lcoe_single_param in ["loan_years"]:
                range_values = np.linspace(single_range_min, single_range_max, int(single_num_steps)).astype(int)
            else:
                range_values = np.linspace(single_range_min, single_range_max, int(single_num_steps))
            
            # Perform sensitivity analysis
            with st.spinner("Calculating sensitivity..."):
                sensitivity_results = perform_sensitivity_analysis(params, lcoe_single_param, range_values)
            
            # Create line chart
            fig = px.line(
                sensitivity_results, 
                x='Parameter_Value', 
                y="LCOE",
                markers=True,
                title=f"LCOE Sensitivity to {lcoe_single_param}",
                labels={
                    'Parameter_Value': {
                        "solar_capacity_kw": "Solar Capacity (kW)",
                        "wind_capacity_kw": "Wind Capacity (kW)",
                        "interest_rate": "Interest Rate (%)",
                        "loan_years": "System Lifetime (years)",
                        "battery_capacity_kwh": "Battery Capacity (kWh)"
                    }.get(lcoe_single_param, lcoe_single_param),
                    "LCOE": "LCOE (€/kWh)"
                }
            )
            
            # Update layout
            fig.update_layout(
                xaxis_title={
                    "solar_capacity_kw": "Solar Capacity (kW)",
                    "wind_capacity_kw": "Wind Capacity (kW)",
                    "interest_rate": "Interest Rate (%)",
                    "loan_years": "System Lifetime (years)",
                    "battery_capacity_kwh": "Battery Capacity (kWh)"
                }.get(lcoe_single_param, lcoe_single_param),
                yaxis_title="LCOE (€/kWh)",
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Find optimal point
            min_lcoe_idx = sensitivity_results['LCOE'].idxmin()
            min_lcoe = sensitivity_results.loc[min_lcoe_idx, 'LCOE']
            optimal_param_value = sensitivity_results.loc[min_lcoe_idx, 'Parameter_Value']
            
            st.success(f"Optimal {lcoe_single_param} value: {optimal_param_value:.2f}, yielding LCOE = {min_lcoe:.4f} €/kWh")

if __name__ == "__main__":
    main()import streamlit as st
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

def calculate_lcoe(energy_capex, annual_opex, annual_energy_production, discount_rate, lifetime):
    """
    Calculate the Levelized Cost of Energy (LCOE)
    
    Parameters:
    energy_capex (float): Capital expenditure for energy system
    annual_opex (float): Annual operating expenses
    annual_energy_production (float): Annual energy production in kWh
    discount_rate (float): Discount rate as a percentage (e.g., 5.0 for 5%)
    lifetime (int): System lifetime in years
    
    Returns:
    float: LCOE in €/kWh
    """
    discount_rate = discount_rate / 100  # Convert percentage to decimal
    
    # Initialize present value sums
    pv_costs = energy_capex  # Initial CAPEX is already in present value
    pv_energy = 0
    
    # Calculate present values for each year
    for year in range(1, lifetime + 1):
        # Present value of OPEX for this year
        pv_costs += annual_opex / ((1 + discount_rate) ** year)
        
        # Present value of energy production for this year
        # Assume degradation of 0.5% per year for energy production
        degradation_factor = (1 - 0.005) ** (year - 1)
        yearly_energy = annual_energy_production * degradation_factor
        pv_energy += yearly_energy / ((1 + discount_rate) ** year)
    
    # Calculate LCOE
    if pv_energy > 0:
        lcoe = pv_costs / pv_energy
    else:
        lcoe = float('inf')
        
    return lcoe

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
    
    # Energy system parameters (extract if available or use defaults)
    solar_capacity_kw = params.get("solar_capacity_kw", 10)
    wind_capacity_kw = params.get("wind_capacity_kw", 3)
    battery_capacity_kwh = params.get("battery_capacity_kwh", 30)
    solar_capex = params.get("solar_pv_capex", 15000)
    wind_capex = params.get("wind_turbine_capex", 12000)
    battery_capex = params.get("battery_capex", 36000)

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
        }
    }
    
    # Add detailed CAPEX breakdown if available
    if detailed_capex_breakdown:
        result["detailed_capex_breakdown"] = detailed_capex_breakdown
    
    # Calculate LCOE metrics
    # Extract energy system components from CAPEX if available
    energy_capex = 0
    if "detailed_capex" in params:
        solar_capex = params["detailed_capex"].get(f"Solar PV ({solar_capacity_kw}kWp)", 0)
        wind_capex = params["detailed_capex"].get(f"Wind Turbine ({wind_capacity_kw}kW)", 0) 
        battery_capex = params["detailed_capex"].get(f"Battery Storage ({battery_capacity_kwh}kWh)", 0)
        energy_capex = solar_capex + wind_capex + battery_capex
    else:
        # If no detailed breakdown, estimate energy portion of microgrid
        energy_capex = microgrid_capex * 0.7  # Assume 70% of microgrid cost is energy-related
    
    # Energy production estimates
    # Capacity factors (typical values)
    solar_capacity_factor = 0.15  # 15% capacity factor for solar
    wind_capacity_factor = 0.30   # 30% capacity factor for wind
    
    # Calculate annual energy production in kWh
    annual_solar_production = solar_capacity_kw * 8760 * solar_capacity_factor
    annual_wind_production = wind_capacity_kw * 8760 * wind_capacity_factor
    total_annual_energy = annual_solar_production + annual_wind_production
    
    # Energy-related OPEX (estimated as percentage of total maintenance)
    energy_opex = maintenance_opex * 0.4  # Assume 40% of maintenance is for energy system
    
    # Calculate LCOE
    lcoe = calculate_lcoe(
        energy_capex=energy_capex,
        annual_opex=energy_opex,
        annual_energy_production=total_annual_energy,
        discount_rate=interest_rate,
        lifetime=loan_years
    )
    
    # Add LCOE metrics to result
    result["lcoe"] = lcoe
    result["energy_capex"] = energy_capex
    result["energy_opex"] = energy_opex
    result["annual_energy_production"] = total_annual_energy
    result["solar_annual_production"] = annual_solar_production
    result["wind_annual_production"] = annual_wind_production
    result["energy_breakdown"] = {
        "Solar PV": annual_solar_production,
        "Wind Turbine": annual_wind_production
    }
    
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

def create_energy_production_chart(energy_data):
    """
    Create a pie chart showing energy production breakdown
    """
    labels = list(energy_data.keys())
    values = list(energy_data.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.4,
        marker_colors=['#FFD700', '#87CEFA']
    )])
    
    fig.update_layout(
        title_text='Annual Energy Production Breakdown (kWh/year)'
    )
    
    return fig

def create_lcoe_comparison_chart(lcoe_value):
    """
    Create a gauge chart for LCOE with comparison markers
    """
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = lcoe_value,
        number = {"suffix": " €/kWh", "valueformat": ".3f"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Levelized Cost of Energy (LCOE)"},
        gauge = {
            'axis': {'range': [None, 1], 'tickwidth': 1},
            'bar': {'color': "#1E88E5"},
            'steps': [
                {'range': [0, 0.10], 'color': '#4CAF50'},  # Green (excellent)
                {'range': [0.10, 0.20], 'color': '#8BC34A'},  # Light green (very good)
                {'range': [0.20, 0.30], 'color': '#FFEB3B'},  # Yellow (good)
                {'range': [0.30, 0.50], 'color': '#FFC107'},  # Amber (fair)
                {'range': [0.50, 1], 'color': '#F44336'}     # Red (poor)
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': lcoe_value
            }
        }
    ))
    
    # Add reference markers for typical energy costs
    reference_values = [
        {'value': 0.05, 'label': 'Utility Solar'},
        {'value': 0.07, 'label': 'Utility Wind'},
        {'value': 0.15, 'label': 'Residential Solar'},
        {'value': 0.25, 'label': 'Diesel Generator'}
    ]
    
    for ref in reference_values:
        fig.add_shape(
            type="line",
            x0=0.5, y0=ref['value']/1,
            x1=0.6, y1=ref['value']/1,
            line=dict(color="black", width=3),
            xref="paper", yref="y"
        )
        fig.add_annotation(
            x=0.7, y=ref['value']/1,
            text=ref['label'],
            showarrow=False,
            xref="paper", yref="y"
        )
    
    fig.update_layout(height=400)
    
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

def perform_lcoe_sensitivity_analysis(base_params, variable_params):
    """
    Perform sensitivity analysis for LCOE by varying multiple parameters
    
    Parameters:
    base_params (dict): Base parameters
    variable_params (dict): Parameters to vary with their ranges {param: [min, max, steps]}
    
    Returns:
    pd.DataFrame: Results of sensitivity analysis
    """
    results = []
    
    # Function to generate parameter combinations
    def generate_combinations(param_index=0, current_params=None):
        if current_params is None:
            current_params = base_params.copy()
        
        if param_index >= len(variable_params):
            # We've set all parameters, calculate LCOE
            result = calculate_os4p(current_params)
            
            # Store results
            result_row = {param: current_params[param] for param in variable_params.keys()}
            result_row['LCOE'] = result['lcoe']
            result_row['Annual_Energy'] = result['annual_energy_production']
            result_row['Energy_CAPEX'] = result['energy_capex']
            
            results.append(result_row)
            return
        
        # Get current parameter and its range
        param = list(variable_params.keys())[param_index]
        param_range = variable_params[param]
        
        # Generate values in the range
        min_val, max_val, steps = param_range
        values = np.linspace(min_val, max_val, steps)
        
        # For each value, recursively set the remaining parameters
        for value in values:
            temp_params = current_params.copy()
            temp_params[param] = value
            generate_combinations(param_index + 1, temp_params)
    
    # Generate all combinations and calculate LCOE
    generate_combinations()
    
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
    # Calculate Innovation Fund scores for each cost efficiency value
    innovation_scores = []
    
    for index, row in sensitivity_data.iterrows():
        # Calculate cost efficiency for this row
        if row['CO2_Savings_All_Outposts'] > 0:
            # Using a proxy for total_grant / co2_savings since we don't have total_grant in sensitivity data
            # This is just for visualization purposes to show the trend
            ce_ratio = 500000 / row['CO2_Savings_All_Outposts']  # Approximate grant amount / CO2 savings
            score = calculate_innovation_fund_score(ce_ratio)
        else:
            score = 0
            
        innovation_scores.append(score)
    
    # Add scores to the data
    score_data = sensitivity_data.copy()
    score_data['Innovation_Fund_Score'] = innovation_scores
    
    # Create chart
    fig = px.line(
        score_data,
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

        # Main CAPEX inputs
        st.subheader("CAPEX Summary (€ per Outpost)")
        
        # CAPEX Detailed Breakdown toggle
        show_capex_detail = st.checkbox("Show detailed CAPEX breakdown", value=False)
        
        if show_capex_detail:
            st.markdown("#### Microgrid CAPEX Breakdown")
            solar_capacity_kw = st.number_input("Solar PV System Capacity (kW)", min_value=5, max_value=50, value=10, step=1, format="%d")
            solar_pv_capex = st.number_input(f"Solar PV System ({solar_capacity_kw}kWp)", min_value=5000, max_value=50000, value=15000, step=1000, format="%d")
            
            wind_capacity_kw = st.number_input("Wind Turbine Capacity (kW)", min_value=1, max_value=10, value=3, step=1, format="%d")
            wind_turbine_capex = st.number_input(f"Wind Turbine ({wind_capacity_kw}kW)", min_value=5000, max_value=50000, value=12000, step=1000, format="%d")
            
            battery_capacity_kwh = st.number_input("Battery Storage Capacity (kWh)", min_value=10, max_value=100, value=30, step=5, format="%d")
            battery_capex = st.number_input(f"Battery Storage ({battery_capacity_kwh}kWh)", min_value=10000, max_value=100000, value=36000, step=1000, format="%d")
            
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