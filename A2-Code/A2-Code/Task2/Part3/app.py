from flask import Flask, request, jsonify, render_template
import hashlib
import json
import os
import datetime
from config import NODES, CONSENSUS_THRESHOLD, REQUIRED_APPROVALS, TOTAL_NODES, PKG, PROCUREMENT_OFFICER

global_sequence_number = 0
app = Flask(__name__)

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

class HarnMultiSignature:
    @staticmethod
    def generate_secret_key(identity):
        return pow(identity, PKG.d, PKG.n)


    @staticmethod
    def sign_message(node_id, message):
        node = NODES[node_id]
        g_i = HarnMultiSignature.generate_secret_key(node.identity)
        r_i = node.random_val
        h = int(hashlib.sha256(message.encode()).hexdigest(), 16) % PKG.n
        return (g_i * pow(r_i, h, PKG.n)) % PKG.n


def encrypt_message_harn(message, recipient_identity):
    """
    Encrypts a message using recipient's identity as their public key.
    """
    message_bytes = message.encode('utf-8')
    m = int.from_bytes(message_bytes, 'big')
    # Use recipient identity as a public key (e = identity)
    e = recipient_identity
    n = PKG.n
    c = pow(m, e, n)
    return c


def decrypt_message_harn(ciphertext, recipient_identity):
    """
    Decrypts a message using the recipient's identity-derived secret key.
    """
    # Retrieve recipient's secret key using PKG
    d = HarnMultiSignature.generate_secret_key(recipient_identity)
    n = PKG.n
    m = pow(ciphertext, d, n)
    # Convert int back to string
    message_bytes = m.to_bytes((m.bit_length() + 7) // 8, 'big')
    return message_bytes.decode('utf-8')


# Initialise nodes

nodes = {name: RSANode(name, params.p, params.q, params.e) for name, params in NODES.items()}

def generate_signature(record, node_id):
    return HarnMultiSignature.sign_message(node_id, record)


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
    """Determine if a node is primary for the current view"""
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

@app.route('/api/node-info')
def get_node_info():
    node_info = {
        "pkg": {
            "p": str(PKG.p),
            "q": str(PKG.q),
            "n": str(PKG.n),
            "e": str(PKG.e),
            "d": str(PKG.d)
        },
        "nodes": {
            name: {
                "id": name,
                "identity": str(node.identity),
                "random_val": str(node.random_val),
                "secret_key": str(HarnMultiSignature.generate_secret_key(node.identity))
            } for name, node in NODES.items()
        }
    }
    return jsonify(node_info)

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
                    "is_primary": record.get("is_primary", False),
                    "partial_signatures": record.get("partial_signatures", []),

                }
                results.append(result)
        except (KeyError, AttributeError):
            continue

    unique_results = list({json.dumps(record, sort_keys=True) for record in results})
    unique_results = [json.loads(r) for r in unique_results]

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
    os.makedirs("Task2/Part3/database", exist_ok=True)
    path = os.path.join("Task2/Part3", "database", f"node_{node.lower()}.json")
    if not os.path.exists(path):
        return {"records": []}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return {"records": []}

def save_db(node, data):
    os.makedirs("Task2/Part3/database", exist_ok=True)
    path = os.path.join("Task2/Part3", "database", f"node_{node.lower()}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)
        


# Route for submitting a record
# In app.py

@app.route('/submit', methods=['POST'])
def submit():
    global global_sequence_number
    data = request.json
    node = data.get("node")
    record = data.get("record")
    
    print("Received a submit POST request")



    if not node or not record or node not in nodes:
        return jsonify({"error": "Invalid input"}), 400
    print(f"Request JSON data: {data}")

    # Check if this node is the primary for the current view
    current_view = nodes[node].view_number
    primary_node = get_primary_node(current_view)
    is_primary = (node == get_primary_node(current_view))

   
     # Use global sequence number and increment it
    global_sequence_number += 1
    sequence_number = global_sequence_number
    
    # Update the node's sequence number to match (for consistency)
    nodes[node].sequence_number = sequence_number

    # --- Phase 1: Pre-Prepare ---
    # sequence_number = nodes[node].sequence_number + 1
    # nodes[node].sequence_number = sequence_number
    signature = nodes[node].sign(record)
    
    print(f"signature: {signature}")


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
    partial_signatures = []

    if len(prepare_messages) + 1 >= REQUIRED_APPROVALS:  # +1 for primary
        for name in nodes:
            commit_signature = nodes[name].sign(f"commit:{sequence_number}:{record}")
            commit = {
                'sequence': sequence_number,
                'view': current_view,
                'phase': 'commit',
                'record': record,
                'signature': commit_signature,
                'sender': name
            }
            nodes[name].commit_messages[(sequence_number, current_view)] = commit
            nodes[name].message_log.append(commit)
            commit_messages.append(commit)

            # Collect partial signature and who signed it
            partial_signatures.append({
                "signature": str(commit_signature),
                "signed_by": name   
            })

        # Save the record only once consensus is reached
        committed_record = {
            "record": record,
            "signature": str(signature),
            "status": "committed",
            "verified_by": "PBFT",
            "sequence": sequence_number,
            "view": current_view,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "is_primary": is_primary,
            "partial_signatures": partial_signatures  # <-- ADD this line
        }

        inventory_ledger.append(committed_record)


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
                "is_primary": is_primary,
                "partial_signatures": partial_signatures  # <-- ADD this line

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
                "is_primary": is_primary,
                "partial_signatures": partial_signatures  # <-- ADD this line
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
        "is_primary": is_primary
    })

    
    
    
    
# Route to check system status
@app.route('/status')
def status():
    system_status = get_system_status()
    return jsonify(system_status)

@app.route('/view-change', methods=['POST'])
def view_change():
    data = request.json
    node = data.get("node")
    new_view = data.get("view")

    if not node or not new_view or node not in nodes:
        return jsonify({"error": "Invalid input"}), 400

    # Only allow view change if current node is the next primary
    expected_primary = get_primary_node(new_view)
    new_primary = get_primary_node(new_view)
    if node != expected_primary:
        return jsonify({"error": "Only next primary can initiate view change"}), 403

    # Collect prepare and commit messages from the last stable checkpoint
    checkpoint_messages = []
    for name in nodes:
        checkpoint_messages.extend(nodes[name].message_log[-10:])  # Last 10 messages as checkpoint

    # Update all nodes to new view
    for name in nodes:
        nodes[name].view_number = new_view
        nodes[name].sequence_number = max(nodes[name].sequence_number, 0)  # Reset if needed

    return jsonify({
        "status": "View changed",
        "new_view": new_view,
        "primary": expected_primary,
        "checkpoint_messages": checkpoint_messages,
        "old_primary": get_primary_node(new_view - 1)
    })
    
@app.route('/api/verify-query', methods=['POST'])
def verify_query():
    data = request.json
    item_id = data.get('item_id')
    
    if not item_id:
        return jsonify({"error": "Item ID required"}), 400
    
    # Get records from all nodes
    results = []
    partial_signatures = []
    for node in nodes:
        db = get_db(node)
        for record in db["records"]:
            try:
                if "record" not in record or not isinstance(record["record"], str):
                    continue
                parts = record["record"].split(":")
                if len(parts) >= 2 and parts[1] == item_id:
                    results.append({
                        "node": parts[0],
                        "item_id": parts[1],
                        "quantity": int(parts[2]) if len(parts) > 2 else None,
                        "price": int(parts[3]) if len(parts) > 3 else None,
                        "signature": record.get("signature")
                    }) 
                    
                    partial_sig = HarnMultiSignature.sign_message(node, record["record"])
                    partial_signatures.append({
                        "node": node,
                        "partial_signature": str(partial_sig)
                    })
            except (KeyError, AttributeError, ValueError):
                continue

    if not results:
        return jsonify({"error": "Item not found"}), 404

    # Combine signatures
    combined_signature = 1
    for sig in partial_signatures:
        combined_signature = (combined_signature * int(sig["partial_signature"])) % PKG.n

    # Prepare response data
    response_data = {
        "item_id": item_id,
        "results": results,
        "partial_signatures": partial_signatures,
        "combined_signature": str(combined_signature),
        "verification_status": "verified" if len(partial_signatures) >= REQUIRED_APPROVALS else "pending"
    }
    print(f"Response to client: {response_data}")

    
    # Encrypt with Procurement Officer's public key
    message = json.dumps(response_data).encode()
    message_int = int.from_bytes(message, 'big')
    if message_int >= PROCUREMENT_OFFICER.n:
        message_int = message_int % PROCUREMENT_OFFICER.n
    encrypted = pow(message_int, PROCUREMENT_OFFICER.e, PROCUREMENT_OFFICER.n)
    
    return jsonify({
        "encrypted_response": str(encrypted),
        "verification_parameters": {
            "combined_signature": str(combined_signature),
            "partial_signatures": partial_signatures,
            "pkg_n": str(PKG.n),
            "pkg_e": str(PKG.e)
        }
    })

@app.route('/api/decrypt', methods=['POST'])
def decrypt():
    data = request.json
    encrypted = data.get('encrypted')
    
    if not encrypted:
        return jsonify({"error": "Missing encrypted message"}), 400
    
    try:
        encrypted_int = int(encrypted)
        if encrypted_int >= PROCUREMENT_OFFICER.n:
            encrypted_int = encrypted_int % PROCUREMENT_OFFICER.n
        
        decrypted_int = pow(encrypted_int, PROCUREMENT_OFFICER.d, PROCUREMENT_OFFICER.n)
        byte_length = (decrypted_int.bit_length() + 7) // 8
        decrypted_bytes = decrypted_int.to_bytes(byte_length, 'big')
        
        try:
            # Try UTF-8 first
            try:
                plaintext = decrypted_bytes.decode('utf-8')
            except UnicodeDecodeError:
                plaintext = decrypted_bytes.hex()  # or base64 if that's what you used before encryption

            try:
                decrypted_data = json.loads(plaintext)
                return jsonify({
                    "success": True,
                    "decrypted": decrypted_data,
                    "format": "json"
                })
            except json.JSONDecodeError:
                return jsonify({
                    "success": True,
                    "decrypted": plaintext,
                    "format": "text"
                })
        except UnicodeDecodeError:
            # If UTF-8 fails, try to parse as raw JSON bytes
            try:
                decrypted_data = json.loads(decrypted_bytes)
                return jsonify({
                    "success": True,
                    "decrypted": decrypted_data,
                    "format": "json_bytes"
                })
            except json.JSONDecodeError:
                return jsonify({
                    "success": True,
                    "decrypted_hex": decrypted_bytes.hex(),
                    "format": "hex"
                })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Decryption failed: {str(e)}"
        }), 400
    
    
if __name__ == '__main__':
    app.run(debug=True)
