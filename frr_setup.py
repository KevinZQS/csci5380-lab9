import os
import docker

BRIDGE_NAME = "bgp-net"
BRIDGE_SUBNET = "192.168.50.0/24"
BRIDGE_GATEWAY = "192.168.50.1"

BGP_ROUTER_CONTAINER = "lab9-frr"
BGP_ROUTER_IP = "192.168.50.3"
LOCAL_BGP_AS = 65001
LOCAL_ROUTER_ID = "1.1.1.1"

PEER_IP = "192.168.50.5"
PEER_AS = 65020

BGP_CONFIG_DIR = "/tmp/lab9_frr"

docker_client = docker.from_env()


def ensure_bgp_bridge():
    try:
        bridge = docker_client.networks.get(BRIDGE_NAME)
        print(f"[INFO] Docker network already exists: {BRIDGE_NAME}")
        return bridge
    except docker.errors.NotFound:
        ipam_pool = docker.types.IPAMPool(
            subnet=BRIDGE_SUBNET,
            gateway=BRIDGE_GATEWAY,
        )
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])

        bridge = docker_client.networks.create(
            name=BRIDGE_NAME,
            driver="bridge",
            ipam=ipam_config,
        )
        print(f"[OK] Created Docker network: {BRIDGE_NAME}")
        return bridge


def ensure_bgp_config_dir():
    os.makedirs(BGP_CONFIG_DIR, exist_ok=True)


def write_frr_daemons():
    daemons_content = """\
zebra=yes
bgpd=yes
ospfd=no
ripd=no
isisd=no
ldpd=no
"""
    with open(os.path.join(BGP_CONFIG_DIR, "daemons"), "w") as f:
        f.write(daemons_content)

    print("[OK] Wrote FRR daemons file")


def write_frr_config():
    config = f"""\
frr defaults traditional
hostname {BGP_ROUTER_CONTAINER}
service integrated-vtysh-config
no ipv6 forwarding
!
router bgp {LOCAL_BGP_AS}
 bgp router-id {LOCAL_ROUTER_ID}
 neighbor {PEER_IP} remote-as {PEER_AS}
 network {LOCAL_ROUTER_ID}/32
!
log stdout
"""

    with open(os.path.join(BGP_CONFIG_DIR, "frr.conf"), "w") as f:
        f.write(config)

    print("[OK] Wrote FRR config")


def remove_existing_frr_container():
    try:
        container = docker_client.containers.get(BGP_ROUTER_CONTAINER)
        container.remove(force=True)
        print(f"[INFO] Removed existing container: {BGP_ROUTER_CONTAINER}")
    except docker.errors.NotFound:
        pass


def start_frr_container():
    container = docker_client.containers.run(
        "frrouting/frr:latest",
        name=BGP_ROUTER_CONTAINER,
        detach=True,
        tty=True,
        stdin_open=True,
        privileged=True,
        volumes={BGP_CONFIG_DIR: {"bind": "/etc/frr", "mode": "rw"}},
        hostname=BGP_ROUTER_CONTAINER,
    )
    print(f"[OK] Started FRR container: {BGP_ROUTER_CONTAINER}")
    return container


def attach_frr_to_bridge(container, bridge):
    container.reload()
    bridge.reload()

    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    if BRIDGE_NAME in networks:
        print(f"[INFO] Container already connected to {BRIDGE_NAME}")
        return

    bridge.connect(container, ipv4_address=BGP_ROUTER_IP)
    print(f"[OK] Connected {BGP_ROUTER_CONTAINER} to {BRIDGE_NAME} with IP {BGP_ROUTER_IP}")


def show_frr_status():
    container = docker_client.containers.get(BGP_ROUTER_CONTAINER)
    print("\n=== FRR Container Status ===")
    print(f"[INFO] Name: {container.name}")
    print(f"[INFO] Status: {container.status}")

    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    if BRIDGE_NAME in networks:
        print(f"[INFO] IP on {BRIDGE_NAME}: {networks[BRIDGE_NAME].get('IPAddress')}")


def deploy_frr_service():
    print("=== FRR Automation ===")

    bridge = ensure_bgp_bridge()
    ensure_bgp_config_dir()
    write_frr_daemons()
    write_frr_config()
    remove_existing_frr_container()
    container = start_frr_container()
    attach_frr_to_bridge(container, bridge)
    show_frr_status()

    print("[DONE] FRR setup completed.")


if __name__ == "__main__":
    deploy_frr_service()