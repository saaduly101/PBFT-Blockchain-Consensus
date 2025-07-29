// In submit.js

document.getElementById("recordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const resultDiv = document.getElementById("result");
    resultDiv.innerHTML = "Processing...";

    const node = document.getElementById('node').value;
    const item = document.getElementById('item').value;
    const quantity = document.getElementById('quantity').value;
    const price = document.getElementById('price').value;
    const submitBtn = document.querySelector("#recordForm button[type='submit']");
    const record = `${node}:${item}:${quantity}:${price}`;

    submitBtn.disabled = true;
    submitBtn.innerText = "Processing...";

    try {
        // Step 1: Submit record to primary node
        const submitRes = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node, record })
        });
        
        const submitResult = await submitRes.json();
        if (submitResult.error) {
            throw new Error(submitResult.error);
        }

        // Step 2: Display consensus progress
        let output = `
            <h2>Record Status: ${submitResult.record_status}</h2>
            <p><strong>Sequence:</strong> ${submitResult.sequence}</p>
            <p><strong>View:</strong> ${submitResult.view}</p>
            <p><strong>Consensus Progress:</strong> 
                ${submitResult.prepares_count} prepares, 
                ${submitResult.commits_count} commits
            </p>
        `;

        if (submitResult.record_status === "committed") {
            output += `<p class="success">✅ Record committed to blockchain</p>`;
        } else {
            // Poll for status updates
            const pollStatus = async () => {
                const statusRes = await fetch(`/status?sequence=${submitResult.sequence}&view=${submitResult.view}`);
                const status = await statusRes.json();
                if (status.state === "committed") {
                    output += `<p class="success">✅ Record committed to blockchain</p>`;
                    resultDiv.innerHTML = output;
                } else {
                    setTimeout(pollStatus, 1000);
                }
            };
            pollStatus();
        }

        resultDiv.innerHTML = output;

    } catch (err) {
        resultDiv.innerHTML = `<p class="error">❌ ${err.message}</p>`;
        console.error(err);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Submit Record";
    }
});


