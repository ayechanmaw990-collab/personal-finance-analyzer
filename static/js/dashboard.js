document.addEventListener("DOMContentLoaded", function () {

    // Monthly Income & Expense Chart
    const monthlyElement = document.getElementById("monthlyChart");

    if (monthlyElement && typeof Chart !== "undefined") {

        const labels = JSON.parse(monthlyElement.dataset.labels || "[]");
        const incomeData = JSON.parse(monthlyElement.dataset.income || "[]");
        const expenseData = JSON.parse(monthlyElement.dataset.expense || "[]");

        new Chart(monthlyElement, {
            type: "bar",

            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Income",
                        data: incomeData,
                        backgroundColor: "#198754",
                        borderRadius: 6,
                        barPercentage: 0.65
                    },
                    {
                        label: "Expense",
                        data: expenseData,
                        backgroundColor: "#dc3545",
                        borderRadius: 6,
                        barPercentage: 0.65
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    mode: "index",
                    intersect: false
                },

                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ": ¥" +
                                    Number(context.raw).toLocaleString("ja-JP");
                            }
                        }
                    }
                },

                scales: {
                    x: {
                        grid: { display: false }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return "¥" + Number(value).toLocaleString("ja-JP");
                            }
                        }
                    }
                }
            }
        });
    }


    // Expense by Category Doughnut Chart
    const expenseElement = document.getElementById("expenseChart");

    if (expenseElement && typeof Chart !== "undefined") {

        const categoryLabels = JSON.parse(expenseElement.dataset.categories || "[]");
        const expenseAmounts = JSON.parse(expenseElement.dataset.amounts || "[]");

        if (categoryLabels.length > 0) {

            new Chart(expenseElement, {
                type: "doughnut",

                data: {
                    labels: categoryLabels,

                    datasets: [{
                        label: "Expenses",
                        data: expenseAmounts,

                        backgroundColor: [
                            "#0d6efd",
                            "#dc3545",
                            "#fd7e14",
                            "#198754",
                            "#6f42c1",
                            "#20c997",
                            "#ffc107"
                        ],

                        borderWidth: 3,
                        borderColor: "#ffffff",
                        hoverOffset: 8
                    }]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "68%",

                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                usePointStyle: true,
                                padding: 18
                            }
                        },

                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.label + ": ¥" +
                                        Number(context.raw).toLocaleString("ja-JP");
                                }
                            }
                        }
                    }
                }
            });
        }
    }

});