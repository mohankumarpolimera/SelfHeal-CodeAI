const runBtn = document.getElementById("runBtn");
const logOutput = document.getElementById("logOutput");
const codeOutput = document.getElementById("codeOutput");

runBtn.addEventListener("click", async () => {
    const userInput = document.getElementById("userInput").value.trim();
    if (!userInput) return alert("Please enter a coding request.");

    logOutput.textContent = "Starting workflow...\n";
    codeOutput.textContent = "";

    try {
        const response = await fetch("/run_workflow", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: userInput })
        });

        const data = await response.json();

        // Display logs from each agent
        data.logs.forEach(log => {
            logOutput.textContent += log + "\n";
        });

        // Display final healed code
        codeOutput.textContent = data.final_code;

    } catch (err) {
        logOutput.textContent += "Error: " + err.message;
    }
});
