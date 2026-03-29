import openstack
from openstack.exceptions import ConflictException
from config import SECGROUP_NAME

conn = openstack.connect()


def ensure_security_group(name: str):
    sec_group = conn.network.find_security_group(name)
    if sec_group:
        print(f"[INFO] Security group already exists: {name}")
        return sec_group

    sec_group = conn.network.create_security_group(
        name=name,
        description="Lab 9 security group for ICMP/SSH/TCP/UDP testing",
    )
    print(f"[OK] Created security group: {name}")
    return sec_group


def ensure_rule(
    sec_group,
    protocol: str,
    direction: str = "ingress",
    ethertype: str = "IPv4",
    port_min=None,
    port_max=None,
    remote_ip_prefix=None,
    description: str = "",
):
    try:
        conn.network.create_security_group_rule(
            security_group_id=sec_group.id,
            direction=direction,
            ethertype=ethertype,
            protocol=protocol,
            port_range_min=port_min,
            port_range_max=port_max,
            remote_ip_prefix=remote_ip_prefix,
            description=description if description else None,
        )
        print(
            f"[OK] Added rule: "
            f"{protocol} {port_min or ''}-{port_max or ''} {remote_ip_prefix or ''}".strip()
        )
    except ConflictException:
        print(
            f"[INFO] Rule already exists: "
            f"{protocol} {port_min or ''}-{port_max or ''} {remote_ip_prefix or ''}".strip()
        )


def setup_security_group():
    print("=== Security Group Automation ===")

    sec_group = ensure_security_group(SECGROUP_NAME)

    ensure_rule(
        sec_group=sec_group,
        protocol="icmp",
        description="Allow ICMP ingress",
    )

    ensure_rule(
        sec_group=sec_group,
        protocol="tcp",
        port_min=22,
        port_max=22,
        remote_ip_prefix="0.0.0.0/0",
        description="Allow SSH ingress",
    )

    ensure_rule(
        sec_group=sec_group,
        protocol="tcp",
        port_min=1,
        port_max=65535,
        remote_ip_prefix="0.0.0.0/0",
        description="Allow all TCP ingress",
    )

    ensure_rule(
        sec_group=sec_group,
        protocol="udp",
        port_min=1,
        port_max=65535,
        remote_ip_prefix="0.0.0.0/0",
        description="Allow all UDP ingress",
    )

    print("[DONE] Security group setup completed.")


if __name__ == "__main__":
    setup_security_group()