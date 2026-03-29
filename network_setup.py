import openstack
from openstack.exceptions import ResourceNotFound

from config import NETWORK_A, NETWORK_B, PUBLIC_NETWORK

# You can move these into config.py later if you want.
ROUTER_NAME = "lab2-router"

SUBNET_A_NAME = "VN-A-Subnet"
SUBNET_A_CIDR = "192.168.100.0/24"
SUBNET_A_GATEWAY = "192.168.100.1"

SUBNET_B_NAME = "VN-B-subnet"
SUBNET_B_CIDR = "192.168.200.0/24"
SUBNET_B_GATEWAY = "192.168.200.1"

DNS_NAMESERVERS = ["8.8.8.8", "8.8.4.4"]

conn = openstack.connect()


def ensure_network(network_name: str):
    network = conn.network.find_network(network_name)
    if network:
        print(f"[INFO] Network already exists: {network.name}")
        return network

    network = conn.network.create_network(name=network_name)
    print(f"[OK] Created network: {network.name}")
    return network


def ensure_subnet(
    subnet_name: str,
    network,
    cidr: str,
    gateway_ip: str,
):
    subnet = conn.network.find_subnet(subnet_name)
    if subnet:
        print(f"[INFO] Subnet already exists: {subnet.name}")
        return subnet

    subnet = conn.network.create_subnet(
        name=subnet_name,
        network_id=network.id,
        ip_version=4,
        cidr=cidr,
        gateway_ip=gateway_ip,
        dns_nameservers=DNS_NAMESERVERS,
        enable_dhcp=True,
    )
    print(f"[OK] Created subnet: {subnet.name} ({cidr})")
    return subnet


def ensure_router(router_name: str):
    router = conn.network.find_router(router_name)
    if router:
        print(f"[INFO] Router already exists: {router.name}")
        return router

    router = conn.network.create_router(name=router_name)
    print(f"[OK] Created router: {router.name}")
    return router


def ensure_router_gateway(router, external_network_name: str):
    public_net = conn.network.find_network(external_network_name)
    if not public_net:
        raise RuntimeError(f"Public network not found: {external_network_name}")

    external_gateway_info = getattr(router, "external_gateway_info", None) or {}
    current_net_id = external_gateway_info.get("network_id")

    if current_net_id == public_net.id:
        print(f"[INFO] Router gateway already set to: {external_network_name}")
        return

    conn.network.update_router(
        router,
        external_gateway_info={"network_id": public_net.id},
    )
    print(f"[OK] Router gateway set to public network: {external_network_name}")


def ensure_router_interface(router, subnet):
    # Check whether this subnet is already attached to the router
    router_ports = conn.network.ports(device_id=router.id)

    for port in router_ports:
        fixed_ips = getattr(port, "fixed_ips", []) or []
        for fixed_ip in fixed_ips:
            if fixed_ip.get("subnet_id") == subnet.id:
                print(f"[INFO] Subnet already attached to router: {subnet.name}")
                return

    conn.network.add_interface_to_router(router, subnet_id=subnet.id)
    print(f"[OK] Attached subnet {subnet.name} to router {router.name}")


def setup_virtual_networks():
    print("=== Virtual Network Automation ===")

    net_a = ensure_network(NETWORK_A)
    subnet_a = ensure_subnet(
        subnet_name=SUBNET_A_NAME,
        network=net_a,
        cidr=SUBNET_A_CIDR,
        gateway_ip=SUBNET_A_GATEWAY,
    )

    net_b = ensure_network(NETWORK_B)
    subnet_b = ensure_subnet(
        subnet_name=SUBNET_B_NAME,
        network=net_b,
        cidr=SUBNET_B_CIDR,
        gateway_ip=SUBNET_B_GATEWAY,
    )

    router = ensure_router(ROUTER_NAME)
    ensure_router_gateway(router, PUBLIC_NETWORK)
    ensure_router_interface(router, subnet_a)
    ensure_router_interface(router, subnet_b)

    print("[DONE] Virtual network setup completed.")


if __name__ == "__main__":
    setup_virtual_networks()