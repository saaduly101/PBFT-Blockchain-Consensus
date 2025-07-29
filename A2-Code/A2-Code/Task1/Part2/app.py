from flask import Flask, request, jsonify, render_template
import hashlib
import json
import os
import datetime
from config import NODES, CONSENSUS_THRESHOLD, REQUIRED_APPROVALS, TOTAL_NODES
app = Flask(__name__)


global_sequence_number = 0
inventory_ledger = []


# --- RSANode Class Definition ---
class RSANode:
    def __init__(self, name, p, q, e):
        self.name = name
        self.p = p
        self.q = q
        self.e = e
        self.n = p * q
        self.phi = (p - 1) * (q - 1)
        self.d = pow(e, -1, self.phi)
        self.view_number = 0
        self.sequence_number = 0
        self.prepare_messages = {}
        self.commit_messages = {}
        self.message_log = []

    def sign(self, message):
        message_bytes = message.encode()
        h = int.from_bytes(hashlib.sha256(message_bytes).digest(), 'big')
        if h >= self.n:
            h = h % self.n
        return pow(h, self.d, self.n)

    def verify(self, message, signature, signer_name):
        signer = nodes[signer_name]
        signer_e, signer_n = signer.e, signer.n
        message_bytes = message.encode()
        h_original = int.from_bytes(hashlib.sha256(message_bytes).digest(), 'big')
        sig_int = int(signature) if isinstance(signature, str) else signature
        h_recovered = pow(sig_int, signer_e, signer_n)
        return h_original == h_recovered



# Initialise nodes

nodes = {name: RSANode(name, params.p, params.q, params.e) for name, params in NODES.items()}


def verify_signature(record, signature, node_id):
    node_name = list(NODES.keys())[node_id - 1]  # Assumes 1-indexed node_id
    return nodes[node_name].verify(record, signature, node_name)

def aggregate_signatures(signatures):
    return json.dumps(signatures)

def query_inventory(criteria):
    keyword = criteria.lower()
    results = [
        entry for entry in inventory_ledger
        if keyword in entry['record'].lower()
    ]
    return results

def get_system_status():
    return {
        "total_nodes": len(nodes),
        "consensus_threshold": REQUIRED_APPROVALS,
        "records_stored": len(inventory_ledger),
        "global_sequence_number": global_sequence_number, 
        "nodes": [
            {"name": name, "view": node.view_number, "seq": node.sequence_number}
            for name, node in nodes.items()
        ]
    }

# Add this helper function at the top level
def is_primary_node(node_name, view_number):
    return node_name == list(nodes.keys())[view_number % len(nodes)]

# DB helpers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")

def load_inventory_data():
    inventory = {}
    for node in ['A', 'B', 'C', 'D']:
        file_path = os.path.join(DB_DIR, f"node_{node.lower()}.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found, setting inventory to empty.")
            inventory[node] = []
            continue
        try:
            with open(file_path) as f:
                inventory[node] = json.load(f)["records"]
        except json.JSONDecodeError:
            print(f"Warning: {file_path} contains invalid JSON, skipping.")
            inventory[node] = []
    return inventory

INVENTORY = load_inventory_data()

@app.route('/')
def index():
    return render_template('index.html', nodes=NODES.keys())


# inventory query
@app.route('/api/query', methods=['POST'])
def handle_query():
    global INVENTORY
    INVENTORY = load_inventory_data()
    
    data = request.json
    node_id = data.get('node')
    item_id = data.get('item_id')

    if node_id not in INVENTORY:
        return jsonify({"error": "Invalid node ID"}), 400

    results = []
    for record in INVENTORY[node_id]:
        try:
            if "record" not in record or not isinstance(record["record"], str):
                continue
            parts = record["record"].split(":")
            if not item_id or (len(parts) >= 2 and parts[1] == item_id):
                result = {
                    "node_id": parts[0],
                    "item_id": parts[1],
                    "quantity": int(parts[2]) if len(parts) > 2 else None,
                    "price": int(parts[3]) if len(parts) > 3 else None,
                    "signature": record.get("signature"),
                    "status": record.get("status") or f"Verified by {record.get('verified_by')}",
                    "is_primary": record.get("is_primary", False)

                }
                results.append(result)
        except (KeyError, AttributeError):
            continue

    unique_results = {tuple(record.items()) for record in results}
    results = [(record) for record in unique_results]


    return jsonify({
        "success": True,
        "node_queried": node_id,
        "item_id": item_id,
        "count": len(results),
        "results": results
    })


def get_primary_node(view_number):
    if not nodes:  # Handle empty node list
        return None
    return list(nodes.keys())[view_number % len(nodes)]

def get_db(node):
    os.makedirs("Task1/Part2/database", exist_ok=True)
    path = os.path.join("Task1", "Part2", "database", f"node_{node.lower()}.json")
    if not os.path.exists(path):
        return {"records": []}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return {"records": []}

def save_db(node, data):
    os.makedirs("Task1/Part2/database", exist_ok=True)
    path = os.path.join("Task1", "Part2", "database", f"node_{node.lower()}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)
        


# Route for submitting a record
@app.route('/submit', methods=['POST'])
def submit():
    global global_sequence_number
    data = request.json
    node = data.get("node")
    record = data.get("record")


    if not node or not record or node not in nodes:
        return jsonify({"error": "Invalid input"}), 400

    # Check if this node is the primary for the current view
    current_view = nodes[node].view_number
    is_primary = (node == get_primary_node(current_view))

   
     # Use global sequence number and increment it
    global_sequence_number += 1
    sequence_number = global_sequence_number
    
    # Update the node's sequence number to match (for consistency)
    nodes[node].sequence_number = sequence_number

    # --- Phase 1: Pre-Prepare ---
    
    signature = nodes[node].sign(record)

    # Store pre-prepare message
    pre_prepare = {
        'sequence': sequence_number,
        'view': current_view,
        'phase': 'pre-prepare',
        'record': record,
        'signature': signature,
        'sender': node,
        'is_primary': is_primary
    }
    nodes[node].message_log.append(pre_prepare)

    # --- Phase 2: Prepare ---
    prepare_messages = []
    for name in nodes:
        if name == node:
            continue

        # Each replica verifies the pre-prepare
        if not nodes[name].verify(record, signature, node):
            continue

        prepare = {
            'sequence': sequence_number,
            'view': current_view,
            'phase': 'prepare',
            'record': record,
            'signature': nodes[name].sign(f"{sequence_number}:{current_view}:{record}"),
            'sender': name
        }
        nodes[name].prepare_messages[(sequence_number, current_view)] = prepare
        nodes[name].message_log.append(prepare)
        prepare_messages.append(prepare)

    # --- Phase 3: Commit ---
    commit_messages = []
    consensus_reached = False
    print(len(prepare_messages))
    if len(prepare_messages) + 1 >= REQUIRED_APPROVALS:  # +1 for primary
        for name in nodes:
            commit = {
                'sequence': sequence_number,
                'view': current_view,
                'phase': 'commit',
                'record': record,
                'signature': nodes[name].sign(f"commit:{sequence_number}:{current_view}:{record}"),
                'sender': name
            }
            nodes[name].commit_messages[(sequence_number, current_view)] = commit
            nodes[name].message_log.append(commit)
            commit_messages.append(commit)

    # --- Check if consensus threshold met ---
    print(f"Commit messages count: {len(commit_messages)}")
    if len(commit_messages) + 1 >= REQUIRED_APPROVALS:  # +1 for primary
        status = "committed"
        # Apply to all nodes' databases
        for name in nodes:
            db = get_db(name)
            db["records"].append({
                "record": record,
                "signature": str(signature),
                "status": "committed",
                "verified_by": "PBFT",
                "sequence": sequence_number,
                "view": current_view,
                "timestamp": datetime.datetime.now().isoformat(),
                "is_primary": is_primary
            })
            save_db(name, db)
            inventory_ledger.append({
                "record": record,
                "signature": str(signature),
                "status": "committed",
                "verified_by": "PBFT",
                "sequence": sequence_number,
                "view": current_view,
                "timestamp": datetime.datetime.now().isoformat(),
                "is_primary": is_primary
            })
    else:
        status = "pending"

    return jsonify({
        "status": f"Consensus {status}",
        "record_status": status,
        "record": record,
        "signature": str(signature),
        "sequence": sequence_number,
        "view": current_view,
        "prepares_count": len(prepare_messages),
        "commits_count": len(commit_messages),
        "prepares": prepare_messages,
        "commits": commit_messages,
        "is_primary": is_primary,
        "consensus_reached": len(commit_messages) + 1 >= REQUIRED_APPROVALS,
        "pre_prepare": {
            "sender": node,
            "record": record,
            "signature": signature
        },
        "prepares": [
            {
                "sender": msg["sender"],
                "signature": msg["signature"]
            } for msg in prepare_messages
        ],
        "commits": [
            {
                "sender": msg["sender"],
                "signature": msg["signature"]
            } for msg in commit_messages
        ],
        "consensus_reached": consensus_reached
    })

      
if __name__ == '__main__':
    app.run(debug=True)
