document.addEventListener('DOMContentLoaded', async () => {
    const harn = new HarnMultiSignature();
    await harn.init();


    // Render PKG info
    document.getElementById('pkg-info').innerHTML = `
        <h3>PKG Parameters</h3>
        <p>Modulus n: ${harn.pkg.n}</p>
        <p>Public exponent e: ${harn.pkg.e}</p>
        <p>phi(n): 954088232425229706382520201245618381050107064612866210923008411734816762594918263185314644</p>
        <p>Private exponent d: 200741941128288805881102727578608580108883612200449762472742993774612841866556866387286291</p>
    `;
    
    // Render nodes
    const nodesTable = document.getElementById('nodes-table');
    Object.entries(harn.nodes).forEach(([name, node]) => {
        nodesTable.innerHTML += `
            <tr>
                <td>${name}</td>
                <td>${node.identity}</td>
                <td>${node.random_val}</td>
                <td>${node.secret_key}</td>
            </tr>
        `;
    });

});