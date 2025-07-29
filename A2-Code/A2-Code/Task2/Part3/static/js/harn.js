class HarnMultiSignature {
    constructor() {
        this.pkg = null;
        this.nodes = {};
        this.combinedSignature = null;
    }

    async init() {
        const response = await fetch('/api/node-info');
        const data = await response.json();
        this.pkg = data.pkg;
        this.nodes = data.nodes;
    }

    async sign(nodeId, message) {
        const response = await fetch('/api/sign', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({node_id: nodeId, message})
        });
        return await response.json();
    }

    combineSignatures(partialSignatures) {
        let combined = 1n;
        const mod = BigInt(this.pkg.n);
        
        partialSignatures.forEach(sig => {
            combined = (combined * BigInt(sig.partial_signature)) % mod;
        });
        
        this.combinedSignature = combined.toString();
        return this.combinedSignature;
    }

    verify(message, combinedSignature, tCombined) {
        const n = BigInt(this.pkg.n);
        const e = BigInt(this.pkg.e);
        
        // Calculate product of identities
        let identitiesProduct = 1n;
        Object.values(this.nodes).forEach(node => {
            identitiesProduct = (identitiesProduct * BigInt(node.identity)) % n;
        });
        
        // Calculate hash
        const hashInput = tCombined + message;
        const hashHex = sha256(hashInput);
        const h = BigInt('0x' + hashHex) % n;
        
        // Verification equation
        const left = modExp(BigInt(combinedSignature), e, n);
        const right = (identitiesProduct * modExp(BigInt(tCombined), h, n)) % n;
        
        return left === right;
    }
}

// Helper functions
function modExp(base, exp, mod) {
    return base ** exp % mod;
}

async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function verifyCombinedSignature(message, combinedSignature) {
    // Calculate product of identities
    let identitiesProduct = 1n;
    Object.values(this.nodes).forEach(node => {
        identitiesProduct = (identitiesProduct * BigInt(node.identity)) % BigInt(this.pkg.n);
    });

    // Calculate hash
    const hashHex = await sha256(message);
    const h = BigInt('0x' + hashHex) % BigInt(this.pkg.n);
    
    // Calculate right side of verification equation
    const right = (identitiesProduct * modExp(BigInt(combinedSignature.t), h, BigInt(this.pkg.n))) % BigInt(this.pkg.n);
    
    // Calculate left side
    const left = modExp(BigInt(combinedSignature.sigma), BigInt(this.pkg.e), BigInt(this.pkg.n));
    
    return left === right;
}

