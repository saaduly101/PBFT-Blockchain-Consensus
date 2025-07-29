"""Hardcoded RSA keys"""

class NodeConfig:
    def __init__(self, p, q, e):
        self.p = p
        self.q = q
        self.e = e
        self.n = p * q

    def get_public_key(self):
            return (self.e, self.n)

# Simulated nodes configuration
NODES = {
    "A": NodeConfig(
        p=1210613765735147311106936311866593978079938707,
        q=1247842850282035753615951347964437248190231863,
        e=815459040813953176289801
    ),
    "B": NodeConfig(
        p=787435686772982288169641922308628444877260947,
        q=1325305233886096053310340418467385397239375379,
        e=692450682143089563609787
    ),
    "C": NodeConfig(
        p=1014247300991039444864201518275018240361205111,
        q=904030450302158058469475048755214591704639633,
        e=1158749422015035388438057
    ),
    "D": NodeConfig(
        p=1287737200891425621338551020762858710281638317,
        q=1330909125725073469794953234151525201084537607,
        e=33981230465225879849295979
    )
}

TOTAL_NODES = 4
CONSENSUS_PROTOCOL = "PBFT"
MAX_FAULTY_NODES = 1  # f=1 for 4 nodes # Ref: https://www.geeksforgeeks.org/minimum-number-of-nodes-to-achieve-byzantine-fault-tolerance/
REQUIRED_APPROVALS = 2 * MAX_FAULTY_NODES + 1  # 3 for f=1
CONSENSUS_THRESHOLD = .75  # Honest Nodes ≥ (Total Nodes / 3) * 2 --> (4/3) * 2 --> (8/3) --> 2.667 out of 4 --> Honest Nodes ≥ 2.66 out of 4 --> 3 out of 4 (round up) --> 0.75