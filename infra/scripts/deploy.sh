#!/usr/bin/env bash
# deploy.sh — Apply BeGuardit K8s manifests in order
# Usage: ./deploy.sh [NAMESPACE]
#
# The namespace argument is optional; defaults to "beguardit".
# Manifests are applied from infra/k8s/ relative to the repo root.

set -euo pipefail

NAMESPACE="${1:-beguardit}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(cd "${SCRIPT_DIR}/../k8s" && pwd)"

echo "==> Deploying BeGuardit to namespace: ${NAMESPACE}"

# 1. Namespace (create if missing)
echo "--- Applying namespace..."
kubectl apply -f "${K8S_DIR}/namespace.yaml"

# 2. Wait for namespace to be active
kubectl wait --for=jsonpath='{.status.phase}'=Active "namespace/${NAMESPACE}" --timeout=30s

# 3. Core services — API, Worker, Portal
echo "--- Applying API deployment + service..."
kubectl apply -f "${K8S_DIR}/api-deployment.yaml" -n "${NAMESPACE}"

echo "--- Applying Worker deployment..."
kubectl apply -f "${K8S_DIR}/worker-deployment.yaml" -n "${NAMESPACE}"

echo "--- Applying Portal deployment + service..."
kubectl apply -f "${K8S_DIR}/portal-deployment.yaml" -n "${NAMESPACE}"

# 4. Apply any additional manifests (ConfigMaps, Ingress, etc.)
for f in "${K8S_DIR}"/*.yaml; do
  base="$(basename "${f}")"
  case "${base}" in
    namespace.yaml|api-deployment.yaml|worker-deployment.yaml|portal-deployment.yaml)
      continue ;;
    *)
      echo "--- Applying ${base}..."
      kubectl apply -f "${f}" -n "${NAMESPACE}" ;;
  esac
done

echo ""
echo "==> Deployment complete. Checking rollout status..."
kubectl rollout status deployment/beguardit-api    -n "${NAMESPACE}" --timeout=120s || true
kubectl rollout status deployment/beguardit-worker -n "${NAMESPACE}" --timeout=120s || true
kubectl rollout status deployment/beguardit-portal -n "${NAMESPACE}" --timeout=120s || true

echo ""
echo "==> Pod status:"
kubectl get pods -n "${NAMESPACE}" -o wide
