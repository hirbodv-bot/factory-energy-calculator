
import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(
    page_title="Factory Energy Cost Calculator",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Factory Energy Cost Calculator")
st.caption("Interactive engineering software for analysing factory energy cost and efficiency.")

with st.sidebar:
    st.header("Scenario Settings")
    energy_reduction = st.slider(
        "Expected energy reduction (%)",
        min_value=0,
        max_value=40,
        value=10,
        step=1
    )
    scenario_tariff = st.slider(
        "Scenario electricity tariff (£/kWh)",
        min_value=0.05,
        max_value=0.80,
        value=0.25,
        step=0.01
    )
    operating_days = st.slider(
        "Operating days per month",
        min_value=1,
        max_value=31,
        value=22,
        step=1
    )

uploaded_file = st.file_uploader(
    "Upload factory Excel data",
    type=["xlsx", "xls"],
    help="The workbook must contain a sheet named Factory_Data."
)

required_columns = [
    "Date",
    "Production Output (units)",
    "Electricity Consumption (kWh)",
    "Operating Hours",
    "Downtime (hours)",
    "Defective Units",
    "Electricity Tariff (£/kWh)"
]

def calculate_results(df):
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    numeric_columns = [
        "Production Output (units)",
        "Electricity Consumption (kWh)",
        "Operating Hours",
        "Downtime (hours)",
        "Defective Units",
        "Electricity Tariff (£/kWh)"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["Date"] + numeric_columns)
    df = df[
        (df["Production Output (units)"] > 0) &
        (df["Operating Hours"] > 0)
    ]

    df["Daily Electricity Cost (£)"] = (
        df["Electricity Consumption (kWh)"] *
        df["Electricity Tariff (£/kWh)"]
    )

    df["Energy per Product (kWh/unit)"] = (
        df["Electricity Consumption (kWh)"] /
        df["Production Output (units)"]
    )

    df["Electricity Cost per Product (£/unit)"] = (
        df["Daily Electricity Cost (£)"] /
        df["Production Output (units)"]
    )

    df["Downtime (%)"] = (
        df["Downtime (hours)"] /
        df["Operating Hours"] * 100
    )

    df["Defect Rate (%)"] = (
        df["Defective Units"] /
        df["Production Output (units)"] * 100
    )

    total_energy = df["Electricity Consumption (kWh)"].sum()
    total_production = df["Production Output (units)"].sum()
    current_cost = df["Daily Electricity Cost (£)"].sum()
    sample_days = len(df)

    avg_daily_energy = total_energy / sample_days
    monthly_current_cost = current_cost / sample_days * operating_days
    monthly_scenario_cost = avg_daily_energy * scenario_tariff * operating_days
    monthly_saving = monthly_scenario_cost * energy_reduction / 100
    annual_saving = monthly_saving * 12
    reduced_monthly_cost = monthly_scenario_cost - monthly_saving

    worst_index = df["Energy per Product (kWh/unit)"].idxmax()
    best_index = df["Energy per Product (kWh/unit)"].idxmin()

    summary = {
        "total_energy": total_energy,
        "total_production": total_production,
        "energy_per_product": total_energy / total_production,
        "cost_per_product": current_cost / total_production,
        "monthly_current_cost": monthly_current_cost,
        "monthly_scenario_cost": monthly_scenario_cost,
        "reduced_monthly_cost": reduced_monthly_cost,
        "monthly_saving": monthly_saving,
        "annual_saving": annual_saving,
        "worst_day": df.loc[worst_index, "Date"],
        "worst_value": df.loc[worst_index, "Energy per Product (kWh/unit)"],
        "best_day": df.loc[best_index, "Date"]
    }

    return df, summary

if uploaded_file is None:
    st.info("Upload the sample Excel file to begin the analysis.")
else:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Factory_Data")

        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            st.error("Missing required columns: " + ", ".join(missing))
            st.stop()

        df, summary = calculate_results(df)

        if df.empty:
            st.error("No valid records were found in the uploaded file.")
            st.stop()

        st.success("Analysis completed successfully.")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "Energy per product",
            f"{summary['energy_per_product']:.2f} kWh/unit"
        )
        col2.metric(
            "Cost per product",
            f"£{summary['cost_per_product']:.3f}"
        )
        col3.metric(
            "Scenario monthly cost",
            f"£{summary['monthly_scenario_cost']:,.0f}"
        )
        col4.metric(
            "Estimated annual saving",
            f"£{summary['annual_saving']:,.0f}"
        )

        st.warning(
            f"The least energy-efficient day was "
            f"{summary['worst_day'].strftime('%d %B %Y')}, with "
            f"{summary['worst_value']:.2f} kWh per unit. "
            f"This day should be investigated for downtime, machine idling, "
            f"maintenance issues, process settings, or reduced production output."
        )

        st.subheader("Daily Results")

        display_df = df[[
            "Date",
            "Production Output (units)",
            "Electricity Consumption (kWh)",
            "Daily Electricity Cost (£)",
            "Energy per Product (kWh/unit)",
            "Downtime (%)",
            "Defect Rate (%)"
        ]].copy()

        display_df["Date"] = display_df["Date"].dt.strftime("%d-%b-%Y")

        st.dataframe(
            display_df.style.format({
                "Daily Electricity Cost (£)": "£{:,.2f}",
                "Energy per Product (kWh/unit)": "{:.3f}",
                "Downtime (%)": "{:.2f}%",
                "Defect Rate (%)": "{:.2f}%"
            }),
            use_container_width=True
        )

        st.subheader("Energy Efficiency Chart")

        fig1, ax1 = plt.subplots(figsize=(10, 4.5))
        ax1.bar(
            df["Date"].dt.strftime("%d-%b"),
            df["Energy per Product (kWh/unit)"]
        )
        ax1.set_title("Daily Energy Consumption per Product")
        ax1.set_xlabel("Operating Day")
        ax1.set_ylabel("kWh per unit")
        ax1.tick_params(axis="x", rotation=45)
        fig1.tight_layout()
        st.pyplot(fig1)

        st.subheader("Monthly Electricity Cost Scenarios")

        scenario_names = [
            "Current tariff",
            "New tariff",
            "New tariff + energy saving"
        ]

        scenario_values = [
            summary["monthly_current_cost"],
            summary["monthly_scenario_cost"],
            summary["reduced_monthly_cost"]
        ]

        fig2, ax2 = plt.subplots(figsize=(8, 4.5))
        ax2.bar(scenario_names, scenario_values)
        ax2.set_title("Estimated Monthly Electricity Cost")
        ax2.set_ylabel("Cost (£)")
        ax2.tick_params(axis="x", rotation=15)
        fig2.tight_layout()
        st.pyplot(fig2)

        st.subheader("Scenario Summary")

        summary_table = pd.DataFrame({
            "Metric": [
                "Current estimated monthly cost",
                "Scenario estimated monthly cost",
                "Estimated monthly saving",
                "Estimated annual saving",
                "Best operating day",
                "Least efficient operating day"
            ],
            "Value": [
                f"£{summary['monthly_current_cost']:,.2f}",
                f"£{summary['monthly_scenario_cost']:,.2f}",
                f"£{summary['monthly_saving']:,.2f}",
                f"£{summary['annual_saving']:,.2f}",
                summary["best_day"].strftime("%d %B %Y"),
                summary["worst_day"].strftime("%d %B %Y")
            ]
        })

        st.table(summary_table)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Calculated_Data", index=False)
            summary_table.to_excel(writer, sheet_name="Scenario_Summary", index=False)

        st.download_button(
            label="Download Results as Excel",
            data=output.getvalue(),
            file_name="Factory_Energy_Analysis_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.caption(
            "This is a preliminary engineering screening tool. "
            "Verify all data, assumptions, equations, tariffs, and operational conditions "
            "before using the results for investment or design decisions."
        )

    except Exception as exc:
        st.error(f"Analysis failed: {type(exc).__name__}: {exc}")
