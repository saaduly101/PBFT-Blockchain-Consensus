        async function handleQuery() {
    const node = document.getElementById('query-node').value;
    const itemId = document.getElementById('query-id').value;

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                node: node,
                item_id: itemId 
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            showError(result.error);
            return;
        }

        displayResults(result);
    } catch (error) {
        showError(`Network error: ${error.message}`);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Ensure the query function executes on button click
    document.getElementById("query-button").addEventListener("click", handleQuery);
});

async function handleQuery() {
    const node = document.getElementById("query-node").value;
    const itemId = document.getElementById("query-id").value;

    console.log(`Querying node ${node} for item ${itemId}`); // Debugging output

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ node, item_id: itemId })
        });

        const result = await response.json();
        console.log("Query result:", result); // Debugging output

        if (!result.success) {
            document.getElementById("query-result").innerHTML = `<p>Error: ${result.error}</p>`;
            return;
        }

        displayResults(result);
    } catch (error) {
        document.getElementById("query-result").innerHTML = `<p>Network error: ${error.message}</p>`;
        console.error("Error fetching query:", error);
    }
}

// Function to display results
function displayResults(result) {
    document.getElementById("query-result").innerHTML = `
        <h3>Query Results</h3>
        <pre>${JSON.stringify(result, null, 2)}</pre>
    `;
}

