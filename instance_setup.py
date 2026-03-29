import openstack
from config import (
    PUBLIC_NETWORK,
    NETWORK_A,
    NETWORK_B,
    IMAGE_NAME,
    FLAVOR_NAME,
    KEY_NAME,
    VM1_NAME,
    VM2_NAME,
    VM3_NAME,
    SECGROUP_NAME,
    CREATE_FLOATING_IPS,
)

conn = openstack.connect()


def get_image():
    image = conn.image.find_image(IMAGE_NAME)
    if not image:
        raise RuntimeError(f"Image not found: {IMAGE_NAME}")
    return image


def get_flavor():
    flavor = conn.compute.find_flavor(FLAVOR_NAME)
    if not flavor:
        raise RuntimeError(f"Flavor not found: {FLAVOR_NAME}")
    return flavor


def get_network(network_name: str):
    network = conn.network.find_network(network_name)
    if not network:
        raise RuntimeError(f"Network not found: {network_name}")
    return network


def get_security_group():
    sec_group = conn.network.find_security_group(SECGROUP_NAME)
    if not sec_group:
        raise RuntimeError(f"Security group not found: {SECGROUP_NAME}")
    return sec_group


def server_exists(server_name: str):
    return conn.compute.find_server(server_name)


def wait_for_server_active(server):
    server = conn.compute.wait_for_server(server, wait=300)
    print(f"[OK] Server is ACTIVE: {server.name}")
    return server


def get_server_port(server):
    ports = list(conn.network.ports(device_id=server.id))
    if not ports:
        raise RuntimeError(f"No Neutron port found for server: {server.name}")
    return ports[0]


def get_available_floating_ip(external_network_id: str):
    floating_ips = list(conn.network.ips(status="DOWN"))
    for ip in floating_ips:
        if getattr(ip, "floating_network_id", None) == external_network_id:
            return ip
    return None

def get_existing_floating_ip_for_port(port):
    floating_ips = list(conn.network.ips(port_id=port.id))
    if floating_ips:
        return floating_ips[0]
    return None

def assign_floating_ip(server):
    public_network = get_network(PUBLIC_NETWORK)
    port = get_server_port(server)

    # First: check whether this server port already has a floating IP
    existing_fip = get_existing_floating_ip_for_port(port)
    if existing_fip:
        print(
            f"[INFO] Floating IP already attached to {server.name}: "
            f"{existing_fip.floating_ip_address}"
        )
        return existing_fip

    # Otherwise reuse a DOWN floating IP or create a new one
    floating_ip = get_available_floating_ip(public_network.id)
    if floating_ip:
        print(f"[INFO] Reusing floating IP: {floating_ip.floating_ip_address}")
    else:
        floating_ip = conn.network.create_ip(floating_network_id=public_network.id)
        print(f"[OK] Created floating IP: {floating_ip.floating_ip_address}")

    conn.network.update_ip(floating_ip, port_id=port.id)
    print(f"[OK] Attached floating IP {floating_ip.floating_ip_address} to {server.name}")
    return floating_ip


def create_server(server_name: str, network_name: str):
    existing = server_exists(server_name)
    if existing:
        print(f"[INFO] Server already exists: {server_name}")
        return existing

    image = get_image()
    flavor = get_flavor()
    network = get_network(network_name)
    sec_group = get_security_group()

    create_args = {
        "name": server_name,
        "image_id": image.id,
        "flavor_id": flavor.id,
        "networks": [{"uuid": network.id}],
        "security_groups": [{"name": sec_group.name}],
    }

    # Only include key_name if it exists in OpenStack
    keypair = conn.compute.find_keypair(KEY_NAME)
    if keypair:
        create_args["key_name"] = KEY_NAME
    else:
        print(f"[INFO] Keypair not found, creating server without keypair: {KEY_NAME}")

    server = conn.compute.create_server(**create_args)
    print(f"[OK] Requested server creation: {server_name}")
    return server


def ensure_server(server_name: str, network_name: str):
    server = create_server(server_name, network_name)
    server = conn.compute.get_server(server.id)

    if server.status != "ACTIVE":
        server = wait_for_server_active(server)
    else:
        print(f"[INFO] Server already ACTIVE: {server.name}")

    floating_ip = None
    if CREATE_FLOATING_IPS:
        floating_ip = assign_floating_ip(server)

    return server, floating_ip


def create_lab_instances():
    print("=== Instance Automation ===")

    print("\n[STEP] Creating same-tenant instances in VN-A")
    vm1, vm1_fip = ensure_server(VM1_NAME, NETWORK_A)
    vm2, vm2_fip = ensure_server(VM2_NAME, NETWORK_A)

    print("\n[STEP] Creating multi-tenant instance in VN-B")
    vm3, vm3_fip = ensure_server(VM3_NAME, NETWORK_B)

    print("\n=== Final Instance Summary ===")
    summary = [
        (vm1.name, NETWORK_A, vm1.status, vm1_fip.floating_ip_address if vm1_fip else "N/A"),
        (vm2.name, NETWORK_A, vm2.status, vm2_fip.floating_ip_address if vm2_fip else "N/A"),
        (vm3.name, NETWORK_B, vm3.status, vm3_fip.floating_ip_address if vm3_fip else "N/A"),
    ]

    for name, net, status, fip in summary:
        print(f"[INFO] {name}: network={net}, status={status}, floating_ip={fip}")

    print("[DONE] Instance setup completed.")


if __name__ == "__main__":
    create_lab_instances()