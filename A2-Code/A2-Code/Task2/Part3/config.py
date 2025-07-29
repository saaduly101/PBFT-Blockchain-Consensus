"""Configuration for Harn Identity-Based Multi-Signature System"""

class PKGConfig:
    def __init__(self):
        # PKG Master Key Parameters
        self.p = 1004162036461488639338597000466705179253226703
        self.q = 950133741151267522116252385927940618264103623
        self.e = 973028207197278907211
        self.n = self.p * self.q
        self.phi_n = (self.p - 1) * (self.q - 1)
        self.d = pow(self.e, -1, self.phi_n)  # Private key

class NodeConfig:
    def __init__(self, identity, random_val, p, q, e):
        self.identity = identity
        self.random_val = random_val  # For signing
        self.p = p
        self.q = q
        self.e = e

class ProcurementOfficer:
    def __init__(self):
        self.p = 1080954735722463992988394149602856332100628417
        self.q = 1158106283320086444890911863299879973542293243
        self.e = 106506253943651610547613
        self.n = self.p * self.q
        self.phi_n = (self.p - 1) * (self.q - 1)
        self.d = pow(self.e, -1, self.phi_n)  # Private key

# System Configuration
PKG = PKGConfig()
PROCUREMENT_OFFICER = ProcurementOfficer()

NODES = {
    "A": NodeConfig(identity=126, random_val=621, 
        p=1210613765735147311106936311866593978079938707,
        q=1247842850282035753615951347964437248190231863,
        e=815459040813953176289801),
    
    "B": NodeConfig(identity=127, random_val=721,
        p=787435686772982288169641922308628444877260947,
        q=1325305233886096053310340418467385397239375379,
        e=692450682143089563609787), 
    
    "C": NodeConfig(identity=128, random_val=821,
        p=1014247300991039444864201518275018240361205111,
        q=904030450302158058469475048755214591704639633,
        e=1158749422015035388438057),
    
    "D": NodeConfig(identity=129, random_val=921, 
        p=1287737200891425621338551020762858710281638317,
        q=1330909125725073469794953234151525201084537607,
        e=33981230465225879849295979)
} 

# Cryptographic Parameters
HASH_ALGORITHM = "sha256"
TOTAL_NODES = 4
CONSENSUS_PROTOCOL = "PBFT"
MAX_FAULTY_NODES = 1  # f=1 for 4 nodes # Ref: https://www.geeksforgeeks.org/minimum-number-of-nodes-to-achieve-byzantine-fault-tolerance/
REQUIRED_APPROVALS = 2 * MAX_FAULTY_NODES + 1  # 3 for f=1
CONSENSUS_THRESHOLD = .75  # Honest Nodes ≥ (Total Nodes / 3) * 2 --> (4/3) * 2 --> (8/3) --> 2.667 out of 4 --> Honest Nodes ≥ 2.66 out of 4 --> 3 out of 4 (round up) --> 0.75
