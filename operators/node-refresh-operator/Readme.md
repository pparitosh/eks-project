User Creates NodeRefresh CR with nodeSelector
    ↓
API Server stores CR in etcd
    ↓
Operator watches for NodeRefresh events
    ↓
Operator triggered (CREATE/UPDATE event)
    ↓
OPERATOR WORKFLOW:
    │
    ├─ 1. Parse nodeSelector from CR spec
    ├─ 2. Find matching nodes in cluster
    ├─ 3. Get list of completed nodes from status
    ├─ 4. Select first pending node
    │
    ├─ 5. Block scheduling on node (mark unschedulable)
    ├─ 6. Wait 2 seconds
    │
    ├─ 7. Get all pods running on node
    ├─ 8. Filter out DaemonSet pods
    │
    ├─ 9. For each movable pod:
    │     └─ Evict pod safely (respecting PDB)
    │
    ├─ 10. Wait 5 seconds for stabilization
    │
    ├─ 11. Health check: verify pods are Running
    │
    ├─ 12. Add completed node to status
    ├─ 13. Update CR status in API Server
    │
    └─ 14. Wait for next reconciliation
         (On next trigger, process next pending node)
