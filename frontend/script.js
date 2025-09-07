// frontend/script.js
(function () {
  const promptInput = document.getElementById("prompt");
  const runBtn      = document.getElementById("runBtn");
  const codeOutput  = document.getElementById("codeOutput");
  const logOutput   = document.getElementById("logOutput");
  const validatedEl = document.getElementById("validated");
  const attemptsEl  = document.getElementById("attempts");

  function getPromptText() {
    if (promptInput && typeof promptInput.value === "string") {
      return promptInput.value.trim();
    }
    const ta = document.querySelector("textarea");
    if (ta && typeof ta.value === "string") return ta.value.trim();
    const ce = document.querySelector("[contenteditable='true']");
    if (ce) return (ce.textContent || "").trim();
    return "";
  }

  async function callApi(body) {
    // Try your main endpoint first; fall back to /run if present.
    const endpoints = ["/run_workflow", "/run"];
    let lastErr = null; // ✅ FIX: remove stray "y"

    for (const url of endpoints) {
      try {
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (resp.ok) return await resp.json();
        let txt = "";
        try { txt = await resp.text(); } catch {}
        lastErr = `HTTP ${resp.status}${txt ? ": " + txt : ""}`;
      } catch (e) {
        lastErr = e?.message || String(e);
      }
    }
    throw new Error(lastErr || "No endpoint reachable");
  }

  async function run(evt) {
    evt?.preventDefault(); // ✅ safer than relying on global event

    const prompt = getPromptText();
    if (!prompt) {
      logOutput.textContent = "Please enter a prompt.\n";
      return;
    }

    runBtn.disabled = true;
    codeOutput.textContent = "";
    logOutput.textContent = "Running...\n";
    validatedEl.textContent = "";
    attemptsEl.textContent = "";

    try {
      const data = await callApi({ prompt });

      // Optional logs from backend
      if (Array.isArray(data.logs)) {
        for (const l of data.logs) logOutput.textContent += l + "\n";
      }

      // Render code + meta
      codeOutput.textContent = data.final_code || data.code || "";
      validatedEl.textContent = `validated = ${Boolean(data.validated)}`;
      attemptsEl.textContent  = `attempts = ${data.attempts ?? "?"}/${data.max_attempts ?? "?"}`;

      if (data.program_output && data.program_output.trim()) {
        logOutput.textContent += `\n[program output]\n${data.program_output}\n`;
        }
      // Warnings / issues / errors
      if (Array.isArray(data.validation_warnings) && data.validation_warnings.length) {
        logOutput.textContent += "\n[warnings]\n" + data.validation_warnings.join("\n") + "\n";
      }
      if (Array.isArray(data.validation_issues) && data.validation_issues.length) {
        logOutput.textContent += "\n[issues]\n" + data.validation_issues.join("\n") + "\n";
      }
      if (Array.isArray(data.errors) && data.errors.length) {
        logOutput.textContent += "\n[errors]\n" + data.errors.join("\n---\n") + "\n";
      }

      // Debug trace (if provided)
      if (Array.isArray(data.debug)) {
        logOutput.textContent += "\n[debug]\n" + data.debug.map(d => JSON.stringify(d)).join("\n") + "\n";
      }
    } catch (e) {
      logOutput.textContent += `\nRequest failed: ${e?.message || e}\n`;
    } finally {
      runBtn.disabled = false;
    }
  }

  if (runBtn) runBtn.addEventListener("click", run);
})();
