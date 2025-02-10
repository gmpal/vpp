import React, { useState } from "react";
import { optimizeStrategy, OptimizationRecord } from "./api.ts";
import { Line } from "react-chartjs-2";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Tooltip,
    Legend
} from "chart.js";

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

function OptimizationPage() {
    const [results, setResults] = useState<OptimizationRecord[]>([]);
    const [error, setError] = useState<string | null>(null);

    // For picking start/end times (defaults to 'today' + 24 hours, for example).
    const [start, setStart] = useState<string>(() => {
        const now = new Date();
        return now.toISOString().slice(0, 16); // 'YYYY-MM-DDTHH:mm'
    });
    const [end, setEnd] = useState<string>(() => {
        const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
        return tomorrow.toISOString().slice(0, 16);
    });

    // Handle button click to run the optimization
    const handleOptimize = async () => {
        setError(null);

        try {
            // We pass start/end as ISO strings to the optimization call
            // e.g. "2025-01-01T00:00"
            const startISO = new Date(start).toISOString();
            const endISO = new Date(end).toISOString();

            const data = await optimizeStrategy();
            setResults(data);
        } catch (err: any) {
            setError(err.message);
        }
    };

    // Prepare chart data: let's show battery SOC by time
    // If you have multiple batteries, you can create multiple datasets
    // For simplicity, let's just show them all on the same chart, color-coded by battery_id
    const batteryIds = Array.from(new Set(results.map((row) => row.battery_id)));

    // We'll gather data in the shape needed by react-chartjs-2
    const chartData = {
        labels: results.map((r) => r.time), // x-axis = time
        datasets: batteryIds.map((batId, idx) => {
            // Filter the rows for this battery_id
            const batRows = results.filter((r) => r.battery_id === batId);

            return {
                label: `SOC - ${batId}`,
                data: batRows.map((r) => r.soc),
                borderColor: COLORS[idx % COLORS.length],
                backgroundColor: COLORS[idx % COLORS.length] + "88",
                tension: 0.1
            };
        })
    };

    return (
        <div style={styles.container}>
            <h1>Optimization</h1>
            <div style={styles.controls}>
                <button onClick={handleOptimize} style={styles.button}>
                    Run Optimization
                </button>
            </div>

            {error && <p style={{ color: "red" }}>{error}</p>}

            {/* Chart Section */}
            {results.length > 0 && (
                <div style={{ marginTop: "2rem" }}>
                    <h2>State of Charge Over Time</h2>
                    <Line
                        data={chartData}
                        options={{
                            responsive: true,
                            plugins: {
                                legend: {
                                    position: "top"
                                }
                            },
                            scales: {
                                x: {
                                    title: { display: true, text: "Time" }
                                },
                                y: {
                                    title: { display: true, text: "SOC (kWh)" }
                                }
                            }
                        }}
                    />
                </div>
            )}

            {/* Table Section */}
            {results.length > 0 && (
                <div style={{ marginTop: "2rem" }}>
                    <h2>Detailed Results</h2>
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Battery ID</th>
                                <th>Charge (kW)</th>
                                <th>Discharge (kW)</th>
                                <th>SOC (kWh)</th>
                                <th>Grid Buy (kW)</th>
                                <th>Grid Sell (kW)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.map((row, idx) => (
                                <tr key={idx}>
                                    <td>{row.time}</td>
                                    <td>{row.battery_id}</td>
                                    <td>{row.charge}</td>
                                    <td>{row.discharge}</td>
                                    <td>{row.soc}</td>
                                    <td>{row.grid_buy}</td>
                                    <td>{row.grid_sell}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

// Example color palette for multiple datasets
const COLORS = [
    "rgba(255, 99, 132, 1)", // red
    "rgba(54, 162, 235, 1)", // blue
    "rgba(75, 192, 192, 1)", // green
    "rgba(255, 206, 86, 1)", // yellow
    "rgba(153, 102, 255, 1)", // purple
    "rgba(255, 159, 64, 1)"  // orange
];

const styles: Record<string, React.CSSProperties> = {
    container: {
        margin: "2rem",
        fontFamily: "sans-serif"
    },
    controls: {
        display: "flex",
        gap: "1rem",
        marginBottom: "1rem"
    },
    button: {
        padding: "0.5rem 1rem",
        cursor: "pointer"
    },
    table: {
        borderCollapse: "collapse",
        width: "100%"
    }
};

export default OptimizationPage;
