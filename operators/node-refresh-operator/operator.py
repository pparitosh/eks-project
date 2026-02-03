
import kopf
import kubernetes
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@kopf.on.create('ops.example.com', 'v1', 'noderefreshes')
@kopf.on.update('ops.example.com', 'v1', 'noderefreshes')
def refresh_nodes(spec, status, name, namespace, logger, **kwargs):
    """
    Safely moves pods from old nodes to new nodes with zero downtime.
    Runs when a NodeRefresh resource is created or updated.
    """
    
    # Get user configuration
    node_labels = spec.get('nodeSelector')
    if not node_labels:
        raise kopf.PermanentError("nodeSelector is required")
    
    logger.info(f"Starting node refresh for labels: {node_labels}")
    
    # Connect to Kubernetes API
    k8s_api = kubernetes.client.CoreV1Api()
    
    # Find nodes matching the labels
    label_string = ",".join([f"{key}={val}" for key, val in node_labels.items()])
    
    try:
        matching_nodes = k8s_api.list_node(label_selector=label_string).items
    except Exception as error:
        logger.error(f"Cannot find nodes: {error}")
        raise kopf.TemporaryError(str(error), delay=30)
    
    if not matching_nodes:
        return update_status(namespace, name, 'Completed', 'No nodes found', [])
    
    logger.info(f"Found {len(matching_nodes)} nodes to refresh")
    
    # Track which nodes are already done
    completed_nodes = (status or {}).get('nodesCycled', [])
    pending_nodes = [node for node in matching_nodes 
                     if node.metadata.name not in completed_nodes]
    
    if not pending_nodes:
        return update_status(namespace, name, 'Completed', 
                           'All nodes refreshed', completed_nodes)
    
    # Process one node at a time
    current_node = pending_nodes[0]
    node_name = current_node.metadata.name
    
    logger.info(f"Refreshing node: {node_name}")
    update_status(namespace, name, 'Processing', 
                 f'Working on {node_name}', completed_nodes)
    
    try:
        # Step 1: Block new pods from landing on this node
        logger.info(f"Blocking new pods on {node_name}")
        k8s_api.patch_node(node_name, {"spec": {"unschedulable": True}})
        time.sleep(2)
        
        # Step 2: Find all pods running on this node
        all_pods = k8s_api.list_pod_for_all_namespaces(
            field_selector=f"spec.nodeName={node_name}"
        ).items
        
        # Step 3: Filter out system pods (DaemonSets stay on nodes)
        movable_pods = get_movable_pods(all_pods, logger)
        logger.info(f"Moving {len(movable_pods)} pods from {node_name}")
        
        # Step 4: Safely move each pod (respects Pod Disruption Budgets)
        for pod in movable_pods:
            move_pod_safely(k8s_api, pod, logger)
        
        # Step 5: Wait for pods to stabilize on new nodes
        logger.info("Waiting for pods to stabilize...")
        time.sleep(5)
        
        # Step 6: Verify pods are healthy
        check_pod_health(k8s_api, movable_pods, logger)
        
        # Step 7: Mark this node as complete
        completed_nodes.append(node_name)
        update_status(namespace, name, 'Processing', 
                     f'Completed {node_name}', completed_nodes)
        
        logger.info(f"Successfully refreshed {node_name}")
        
    except kopf.TemporaryError:
        raise
    except Exception as error:
        logger.error(f"Failed to refresh {node_name}: {error}")
        update_status(namespace, name, 'Failed', 
                     f'Error: {str(error)}', completed_nodes)
        raise kopf.TemporaryError(str(error), delay=60)


def get_movable_pods(pods, logger):
    """Returns pods that can be moved (excludes DaemonSets)"""
    movable = []
    for pod in pods:
        is_daemonset = False
        if pod.metadata.owner_references:
            for owner in pod.metadata.owner_references:
                if owner.kind == 'DaemonSet':
                    logger.info(f"Skipping DaemonSet pod: {pod.metadata.name}")
                    is_daemonset = True
                    break
        if not is_daemonset:
            movable.append(pod)
    return movable


def move_pod_safely(k8s_api, pod, logger):
    """Evicts a pod while respecting Pod Disruption Budgets"""
    pod_name = pod.metadata.name
    pod_namespace = pod.metadata.namespace
    
    logger.info(f"Moving pod {pod_namespace}/{pod_name}")
    
    eviction = kubernetes.client.V1Eviction(
        metadata=kubernetes.client.V1ObjectMeta(
            name=pod_name,
            namespace=pod_namespace
        )
    )
    
    try:
        k8s_api.create_namespaced_pod_eviction(pod_name, pod_namespace, eviction)
        logger.info(f"Pod {pod_name} moved successfully")
    except kubernetes.client.exceptions.ApiException as error:
        if error.status == 429:
            logger.warning(f"Cannot move {pod_name} yet (PDB limit). Retrying...")
            raise kopf.TemporaryError("Pod Disruption Budget limit", delay=30)
        else:
            logger.error(f"Failed to move {pod_name}: {error}")
            raise kopf.TemporaryError(str(error), delay=30)


def check_pod_health(k8s_api, pods, logger):
    """Verifies that moved pods are running on new nodes"""
    healthy_count = 0
    for pod in pods:
        try:
            current_pod = k8s_api.read_namespaced_pod(
                pod.metadata.name,
                pod.metadata.namespace
            )
            if current_pod.status.phase == "Running":
                healthy_count += 1
                logger.info(f"Pod {pod.metadata.name} is healthy")
            else:
                logger.warning(f"Pod {pod.metadata.name} status: {current_pod.status.phase}")
        except:
            logger.info(f"Pod {pod.metadata.name} completed or removed")
    
    logger.info(f"Health check: {healthy_count}/{len(pods)} pods running")


def update_status(namespace, name, phase, message, completed_nodes):
    """Updates the NodeRefresh resource status"""
    kopf.patch(namespace, name, {
        'status': {
            'phase': phase,
            'message': message,
            'nodesCycled': completed_nodes
        }
    })
