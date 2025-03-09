from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.form
        result = calculate_os4p(
            num_outposts=int(data["num_outposts"]),
            fuel_consumption=float(data["fuel_consumption"]),
            interest_rate=float(data["interest_rate"]),
            loan_years=int(data["loan_years"]),
            sla_premium=float(data["sla_premium"])
        )
        return jsonify(result)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
