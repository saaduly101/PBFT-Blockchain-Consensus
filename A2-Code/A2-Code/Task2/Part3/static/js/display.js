// Modular exponentiation helper
function modExp(base, exp, mod) {
    let result = 1n;
    base = base % mod;
    while (exp > 0) {
        if (exp % 2n === 1n) result = (result * base) % mod;
        exp = exp / 2n;
        base = (base * base) % mod;
    }
    return result;
}

// SHA-256 hash function returning a BigInt
async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return BigInt('0x' + hashHex);
}

document.addEventListener("DOMContentLoaded", async () => {
    const tValues = [
        BigInt("924557310458718712013264487402131145960397638068504605687003354984010171965713299494943820"),
        BigInt("465846207756861894961492272409872942324819834860512827013926688898633436265338481059370415"),
        BigInt("78151043497445054159280444179492074468410085478065819376129170939641218107753496475414232"),
        BigInt("822647722156477994505052001658171996778199886266488031413434243060906736182562144615387307")
    ];
    const modulus = BigInt("954088232425229706382520201245618381050107066567161988535764573189666148989564060702644969");

    // 1. Product t = t1 * t2 * t3 * t4 mod n
    let t = 1n;
    tValues.forEach(val => t = (t * val) % modulus);
    document.getElementById("step-product-t").textContent = `t = t1 * t2 * t3 * t4 mod n = ${t}`;

    // 2. Hash the message
    const message = "Item 001: Quantity 32, Price 12";
    const hashBigInt = await sha256(t.toString() + message);
    document.getElementById("step-hash-msg").textContent = `Hash(t, m) = ${hashBigInt}`;

    // 3. Calculate individual g_i values (g_i = s_i = ID_i * r_i^hash mod n)
    const identities = [
        BigInt("11111111"),
        BigInt("22222222"),
        BigInt("33333333"),
        BigInt("44444444")
    ];
    let gValues = tValues.map((r_i, i) => {
        const g = (identities[i] * modExp(r_i, hashBigInt, modulus)) % modulus;
        return `g_${i + 1} = ID_${i + 1} * r_${i + 1}^h mod n = ${g}`;
    });
    document.getElementById("step-individual-g").textContent = gValues.join('\n');

    // 4. Final signature step (aggregate, simplified here)
    const finalSig = gValues.reduce((acc, _, i) => (acc * identities[i]) % modulus, 1n);  // Sample logic
    document.getElementById("step-final-signature").textContent = `Final signature (simplified) = ${finalSig}`;
});
