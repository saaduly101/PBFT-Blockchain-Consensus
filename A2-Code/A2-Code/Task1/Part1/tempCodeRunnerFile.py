from flask import Flask, request, jsonify, render_template
import hashlib
import json
import os
import datetime
import time 
from config import NODES, CONSENSUS_THRESHOLD, REQUIRED_APPROVALS, TOTAL_NODES, MAX_FAULTY_NODES

app = Flask(__name__)

F = MAX_FAULTY_NODES  # Max faulty nodes (F=1 for 4 nodes)
PREPARE_THRESHOLD = 2 * F  # 2F prepare messages needed
COMMIT_THRESHOLD = 2 * F + 1  # 2F+1 commit messages needed (3 for F=1)

class RSANode:
    def __init__(self, name, p, q, e):
        self.name = name
        self.p = p
        self.q = q
        self.e = e
        self.n = p * q
        self.phi = (p - 1) * (q - 1)
        self.d = pow(e, -1, self.phi)
        
        self.view_number = 0  # Current view
        self.sequence_number = 0  # Current sequence
        self.prepare_messages = {}  # {sequence: {node: message}}
        self.commit_messages = {}   # {sequence: {node: message}}
        self.message_log = []  # Stores all received messages
        
    def sign(self, message):
        message_bytes = message.encode('utf-8')
        h = int.from_bytes(hashlib.sha256(message_bytes).digest(), 'big')
        
        # Ensure h < n (RSA requirement)
        if h >= self.n:
            h = h % self.n
            
        return pow(h, self.d, self.n) # return signature val
    
    def verify(self, message, signature, signer_name):
        # Get the signer's public key from  config
        signer = NODES[signer_name]
        signer_e, signer_n = signer.e, signer.n

        
        # Compute original hash
        message_bytes = message.encode('utf-8')
        h_original = int.from_bytes(hashlib.sha256(message_bytes).digest(), 'big')
        
        # Convert signature to int if needed
        sig_int = int(signature) if isinstance(signature, str) else signature
        
        # Recover hash using signer's public key
        h_recovered = pow(sig_int, signer_e, signer_n)
        
        print(f"\nVerification by {self.name} for {signer_name}:")
        print(f"Using public key (e,n): ({signer_e}, {signer_n})")
        print(f"Original hash: {h_original}")
        print(f"Recovered hash: {h_recovered}")
        print(f"Hash match: {h_original == h_recovered}")
        
        return {
        'valid': h_original == h_recovered,
        'original_hash': h_original,
        'recovered_hash': h_recovered,
        'e': signer_e,
        'n': signer_n
    }

# Initialise all nodes
nodes = {name: RSANode(name, params.p, params.q, params.e) for name, params in NODES.items()}

def get_db(node):
    
    # Create the directory
    # Get simulated database for a node
    os.makedirs("Part1/database", exist_ok=True)
    
    path = os.path.join("Part1", "database", f"node_{node.lower()}.json")
    if not os.path.exists(path):
        return {"records": []}
    with open(path) as f:
        return json.load(f)

def save_db(node, data):
    # Create the directory
    # Save simulated database for a node
    os.makedirs("Part1/database", exist_ok=True)
    
    path = os.path.join("Part1", "database", f"node_{node.lower()}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent = 1)

def count_approvals(verification_results, proposer):
   #Count explicit verifications + implicit proposer verification
    explicit_approvals = sum(1 for v in verification_results.values() if v['status'] == "Verified")
    return explicit_approvals + 1  # +1 for proposer


# --- PBFT Endpoints ---
@app.route('/')
def index():
    return render_template('index.html', 
                         nodes=list(NODES.keys()),
                         PREPARE_THRESHOLD=PREPARE_THRESHOLD,
                         COMMIT_THRESHOLD=COMMIT_THRESHOLD)

# --- PBFT Phases ---
@app.route('/pre-prepare', methods=['POST'])
def pre_prepare():
    """Phase 1: Leader broadcasts the proposal."""
    data = request.json
    node = data['node']

       # Validate input
    if None in (node, item, qty, price) or node not in nodes:
        return jsonify({"error": "Invalid input"}), 400
    
    # Only primary node can initiate pre-prepare
    current_primary = get_primary_node(nodes[node].view_number)
    if node != current_primary:
        return jsonify({"error": f"Only primary node ({current_primary}) can initiate requests"}), 403
    
    
    record = f"{node}:{data['item']}:{data['quantity']}:{data['price']}"
    signature = nodes[node].sign(record)
    sequence_number = nodes[node].sequence_number + 1

    # Simulate broadcast (in reality, use network calls)
    for name in nodes:
        if name != node:
            nodes[name].prepare_messages[node] = {
                'sequence': sequence_number,
                'view': nodes[node].view_number,
                'phase': 'pre-prepare',
                'record': record,
                'signature': signature,
                'sender': node
            }
    
   # Return immediately - client will check status later
    return jsonify({
        "status": "Pre-prepare initiated",
        "sequence": sequence_number,
        "view": nodes[node].view_number,
        "record": record
        })

@app.route('/prepare', methods=['POST'])
def prepare():
    """Phase 2: Nodes verify and broadcast prepare messages"""
    data = request.json
    node = data.get("node")
    sequence = data.get("sequence")
    view = data.get("view")
    
    # Find matching pre-prepare message
    pre_prepare = next((m for m in nodes[node].message_log 
                       if m['sequence'] == sequence 
                       and m['view'] == view 
                       and m['phase'] == 'pre-prepare'), None)
    
    if not pre_prepare:
        return jsonify({"error": "No matching pre-prepare message"}), 400
    
    # Verify the message
    verification = nodes[node].verify(
        pre_prepare['record'],
        pre_prepare['signature'],
        pre_prepare['sender']
    )
    
    if verification['valid']:
        # Store prepare message
        if sequence not in nodes[node].prepare_messages:
            nodes[node].prepare_messages[sequence] = {}
        nodes[node].prepare_messages[sequence][node] = {
            'view': view,
            'record': pre_prepare['record'],
            'signature': pre_prepare['signature']
        }
        
        # Broadcast prepare to all nodes
        for name in nodes:
            if name != node:
                if sequence not in nodes[name].prepare_messages:
                    nodes[name].prepare_messages[sequence] = {}
                nodes[name].prepare_messages[sequence][node] = {
                    'view': view,
                    'record': pre_prepare['record'],
                    'signature': pre_prepare['signature']
                }
    
    return jsonify({
        "status": "Prepare broadcast",
        "valid": verification['valid'],
        "sequence": sequence,
        "view": view
    })

@app.route('/commit', methods=['POST'])
def commit():
    """Phase 3: Nodes commit after sufficient prepares"""
    data = request.json
    node = data.get("node")
    sequence = data.get("sequence")
    view = data.get("view")
    
    # Check if we have 2F prepare messages
    prepare_count = len(nodes[node].prepare_messages.get(sequence, {}))
    if prepare_count >= PREPARE_THRESHOLD:
        # Store commit message
        if sequence not in nodes[node].commit_messages:
            nodes[node].commit_messages[sequence] = {}
        nodes[node].commit_messages[sequence][node] = True
        
        # Broadcast commit to all nodes
        for name in nodes:
            if sequence not in nodes[name].commit_messages:
                nodes[name].commit_messages[sequence] = {}
            nodes[name].commit_messages[sequence][node] = True
        
        # Check if we have 2F+1 commit messages
        commit_count = len(nodes[node].commit_messages.get(sequence, {}))
        if commit_count >= COMMIT_THRESHOLD:
            # Persist to database
            db = get_db(node)
            db["records"].append({
                "record": next(m['record'] for m in nodes[node].message_log 
                             if m['sequence'] == sequence),
                "signature": next(m['signature'] for m in nodes[node].message_log 
                                if m['sequence'] == sequence),
                "status": "COMMITTED",
                "sequence": sequence,
                "view": view
            })
            save_db(node, db)
            return jsonify({"status": "COMMITTED"})
    
    return jsonify({"status": "PENDING"})


@app.route('/status', methods=['GET'])
def status():
    """Check consensus status for a request"""
    sequence = request.args.get("sequence", type=int)
    view = request.args.get("view", type=int)
    node = request.args.get("node", list(NODES.keys())[0])
    
    # Check if request was committed
    db = get_db(node)
    committed = any(r.get("sequence") == sequence for r in db["records"])
    
    if committed:
        return jsonify({"state": "COMMITTED"})
    
    # Return current progress
    prepare_count = len(nodes[node].prepare_messages.get(sequence, {}))
    commit_count = len(nodes[node].commit_messages.get(sequence, {}))
    
    return jsonify({
        "state": "PENDING",
        "prepares": prepare_count,
        "commits": commit_count,
        "required_prepares": PREPARE_THRESHOLD,
        "required_commits": COMMIT_THRESHOLD
    })

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    node = data.get("node")
    item = data.get("item")
    qty = data.get("quantity")
    price = data.get("price")
    
    # Validate
    if None in (node, item, qty, price) or node not in nodes:
        return jsonify({"error": "Invalid input"}), 400
    
    # Create and sign record
    record = f"{node}:{item}:{qty}:{price}"
    print(f"\nSigning record: '{record}'")
    signature = nodes[node].sign(record)
    print(f"Generated signature: {signature}")
    
    
    
    # Simulate verification by other nodes
    approvals = 0
    verification = {}
    verification_details = {}  # <-- This line was missing and causing the error
    for name, verifier in nodes.items():
        if name != node:
             # Modified verify to return more information
            verification_result = verifier.verify(record, signature, node)
            verified = verification_result['valid']
            
            verification[name] = "Verified" if verified else "Rejected"
            verification_details[name] = {
                'status': verification[name],
                'original_hash': str(verification_result['original_hash']),
                'recovered_hash': str(verification_result['recovered_hash']),
                'public_key': f"({verification_result['e']}, {verification_result['n']})"
            }
            if verified:
                approvals += 1
                # Update each node's simulated database
                db = get_db(name)
                db["records"].append({
                    "record": record,
                    "signature": str(signature),
                    "verified_by": name
                })
                save_db(name, db)
    
    # Check consensus
    required_approvals = int(len(nodes) * CONSENSUS_THRESHOLD)
    if approvals >= required_approvals:
        # Update proposer's database
        db = get_db(node)
        db["records"].append({
            "record": record,
            "signature": str(signature),
            "status": "COMMITTED"
        })
        save_db(node, db)
        status = "COMMITTED"
    else:
        status = "REJECTED"
  
    return jsonify({
        "record": record,
        "signature": str(signature),
        "verification": verification,
        "verification_result": verification_details,  # Add this line
        "approvals": {
        "total": count_approvals(verification_details, node),
        "required": REQUIRED_APPROVALS,
        "total_nodes": TOTAL_NODES,
        "threshold": CONSENSUS_THRESHOLD
    },
        # "required": required_approvals,
        "status": status,
        "propagated": status == "COMMITTED"  # New field
        
    })

    
if __name__ == '__main__':
    # Create Part1/database folders
    os.makedirs("Part1/database", exist_ok=True)
    app.run(debug=True, port=5000)