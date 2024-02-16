import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List

import pykube
import pytest
from pytest_helm_charts.clusters import Cluster
from pytest_helm_charts.k8s.job import wait_for_jobs_to_complete

logger = logging.getLogger(__name__)

namespace_name = "default"

timeout: int = 360


@pytest.mark.smoke
def test_api_working(kube_cluster: Cluster) -> None:
    """Very minimalistic example of using the [kube_cluster](pytest_helm_charts.fixtures.kube_cluster)
    fixture to get an instance of [Cluster](pytest_helm_charts.clusters.Cluster) under test
    and access its [kube_client](pytest_helm_charts.clusters.Cluster.kube_client) property
    to get access to Kubernetes API of cluster under test.
    Please refer to [pykube](https://pykube.readthedocs.io/en/latest/api/pykube.html) to get docs
    for [HTTPClient](https://pykube.readthedocs.io/en/latest/api/pykube.html#pykube.http.HTTPClient).
    """
    assert kube_cluster.kube_client is not None
    assert len(pykube.Node.objects(kube_cluster.kube_client)) >= 1


@pytest.mark.smoke
def test_cluster_info(
    kube_cluster: Cluster, cluster_type: str, test_extra_info: Dict[str, str]
) -> None:
    """Example shows how you can access additional information about the cluster the tests are running on"""
    logger.info(f"Running on cluster type {cluster_type}")
    key = "external_cluster_type"
    if key in test_extra_info:
        logger.info(f"{key} is {test_extra_info[key]}")
    assert kube_cluster.kube_client is not None
    assert cluster_type != ""

@pytest.mark.smoke
def test_crds(
    kube_cluster: Cluster
)-> None:
    """ Check for Kyverno CRDs """
    crds = pykube.CustomResourceDefinition.objects(kube_cluster.kube_client).filter(selector="app.kubernetes.io/name=kyverno")
    crd_count = len(crds)
    logger.info(f"Kyverno CRDs found {crd_count}")
    assert kube_cluster.kube_client is not None
    assert len(crds) > 0

# scope "module" means this is run only once, for the first test case requesting! It might be tricky
# if you want to assert this multiple times
@pytest.fixture(scope="module")
def app_job(kube_cluster: Cluster) -> List[pykube.Job]:
    job = wait_for_jobs_to_complete(
        kube_cluster.kube_client,   
        ["kyverno-crds-install-job"],
        namespace_name,
        timeout,
    )
    return job

# when we start the tests on circleci, we have to wait for pods to be available, hence
# this additional delay and retries
@pytest.mark.smoke
@pytest.mark.upgrade
@pytest.mark.flaky(reruns=5, reruns_delay=10)
def test_jobs_succeeded(kube_cluster: Cluster, app_job: List[pykube.Job]):
    logger.info(f"Checking status for job {app_job}")
    for j in app_job:
        assert int(j.obj["status"]["succeeded"]) == 1
        logger.info(f"Checking job {j}")
